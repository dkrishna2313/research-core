"""
ResearchEngine — end-to-end research pipeline orchestration (RC7 aligned).

The engine coordinates provider calls and analysis stages without embedding
their logic. All stage implementations are injected; the engine is domain-neutral
and provider-neutral.

Stage order:
  1. REQUEST_VALIDATION  (INIT)
  2. PROFILE_RESOLUTION
  3. KNOWLEDGE_RETRIEVAL (RETRIEVAL)
  4. WEB_RETRIEVAL       (RETRIEVAL)
  5. NORMALIZATION       (when evidence_normalizer is provided)
  6. RANKING             (when evidence_ranker is provided)
  7. CLAIM_EXTRACTION    (EXTRACTION)
  8. GAP_ANALYSIS
  9. SYNTHESIS
  10. RESULT_ASSEMBLY    (FINALIZATION)

Dual-pipeline support:
  Legacy components (claim_extractor, gap_analyzer, contradiction_detector)
  accept the old-style protocols from research_core.protocols.analysis.
  RC4-RC6 components (evidence_normalizer, evidence_ranker, rc5_claim_extractor,
  rc6_gap_analyzer) use the RC4-RC6 interfaces.

  When RC4-RC6 components are present, they supersede the legacy components for
  their respective stages. The legacy claim_extractor and gap_analyzer still run
  when rc5/rc6 equivalents are absent, populating result.claims and result.gaps
  from the old-style protocols for backward compatibility.

Status determination:
  - RC6 recommended_status is authoritative: a PARTIAL recommendation from RC6
    always results in PARTIAL, even with a high numeric score.
  - Recoverable provider failures set partial=True regardless.
  - Empty evidence raises ProviderExecutionError (no useful result possible).
  - Synthesis failure returns PARTIAL; all prior artifacts are preserved.
  - strict=True raises IncompleteResearchError instead of returning PARTIAL.

Quality diagnostics:
  - When rc6_gap_analyzer is present, result.gap_analysis carries the full
    RC6 QualityDiagnosticsResult; result.quality is not computed separately.
  - When only legacy components are used, result.quality is computed from
    evidence item-level signals via _compute_quality().
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from research_core.analysis.analyzer import GapAnalyzer as RC6GapAnalyzer
from research_core.analysis.config import GapAnalysisConfig
from research_core.claims.extractor import ClaimExtractor as RC5ClaimExtractor
from research_core.contracts.claims import Claim
from research_core.contracts.contradictions import Contradiction
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import OpenQuestion, ResearchGap
from research_core.contracts.quality import QualityDiagnostics, QualityDimension
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import ResearchResult, ResearchStatus, SynthesisResult
from research_core.contracts.sources import Source
from research_core.contracts.trace import (
    ResearchTrace,
    TraceEvent,
    TraceEventStatus,
    TraceStage,
)
from research_core.exceptions import (
    IncompleteResearchError,
    ProviderExecutionError,
    UnknownProfileError,
)
from research_core.normalization.normalizer import EvidenceNormalizer
from research_core.normalization.ranker import EvidenceRanker
from research_core.protocols.analysis import (
    ClaimExtractor,
    ContradictionDetector,
    GapAnalyzer,
)
from research_core.protocols.knowledge import (
    KnowledgeProvider,
    KnowledgeRetrievalRequest,
)
from research_core.protocols.profiles import ProfileProvider
from research_core.protocols.synthesis import SynthesisInput, Synthesizer
from research_core.protocols.web import WebSearchProvider, WebSearchRequest


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _compute_quality(evidence: tuple[EvidenceItem, ...]) -> QualityDiagnostics:
    """Compute QualityDiagnostics from evidence item signals (legacy pipeline only)."""
    if not evidence:
        return QualityDiagnostics()

    rel: list[float] = []
    auth: list[float] = []
    rec: list[float] = []
    ext: list[float] = []

    for ev in evidence:
        q = ev.quality
        if q.relevance is not None:
            rel.append(q.relevance)
        if q.authority is not None:
            auth.append(q.authority)
        if q.recency is not None:
            rec.append(q.recency)
        if q.extraction_confidence is not None:
            ext.append(q.extraction_confidence)

    def _mean(vals: list[float]) -> float | None:
        return sum(vals) / len(vals) if vals else None

    return QualityDiagnostics(
        relevance=QualityDimension(score=_mean(rel)),
        authority=QualityDimension(score=_mean(auth)),
        recency=QualityDimension(score=_mean(rec)),
        extraction_confidence=QualityDimension(score=_mean(ext)),
    )


class ResearchEngine:
    """Orchestrates the research pipeline from request to structured result.

    All stage implementations are injected at construction time. The engine
    does not instantiate vendor adapters and does not import any LLM SDK.

    Legacy dependencies (backward-compatible):
        profile_provider:       resolves profile IDs in the request
        knowledge_provider:     retrieves evidence from a local knowledge store
        web_search_provider:    retrieves evidence from web search
        claim_extractor:        old-style ClaimExtractor (protocols.analysis)
        contradiction_detector: detects Contradiction objects
        gap_analyzer:           old-style GapAnalyzer (protocols.analysis)
        synthesizer:            produces a SynthesisResult (RC7 Synthesizer protocol)
        clock:                  callable returning timezone-aware datetime

    RC4-RC6 dependencies (structured pipeline):
        evidence_normalizer:    RC4 EvidenceNormalizer
        evidence_ranker:        RC4 EvidenceRanker
        rc5_claim_extractor:    RC5 ClaimExtractor (claims.extractor)
        rc6_gap_analyzer:       RC6 GapAnalyzer (analysis.analyzer)
        gap_analysis_config:    RC6 GapAnalysisConfig
    """

    def __init__(
        self,
        *,
        profile_provider: ProfileProvider | None = None,
        knowledge_provider: KnowledgeProvider | None = None,
        web_search_provider: WebSearchProvider | None = None,
        # Legacy (old-style protocols.analysis)
        claim_extractor: ClaimExtractor | None = None,
        contradiction_detector: ContradictionDetector | None = None,
        gap_analyzer: GapAnalyzer | None = None,
        # RC4-RC6 structured pipeline components
        evidence_normalizer: EvidenceNormalizer | None = None,
        evidence_ranker: EvidenceRanker | None = None,
        rc5_claim_extractor: RC5ClaimExtractor | None = None,
        rc6_gap_analyzer: RC6GapAnalyzer | None = None,
        gap_analysis_config: GapAnalysisConfig | None = None,
        # Common
        synthesizer: Synthesizer | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._profile_provider = profile_provider
        self._knowledge_provider = knowledge_provider
        self._web_search_provider = web_search_provider
        self._claim_extractor = claim_extractor
        self._contradiction_detector = contradiction_detector
        self._gap_analyzer = gap_analyzer
        self._evidence_normalizer = evidence_normalizer
        self._evidence_ranker = evidence_ranker
        self._rc5_claim_extractor = rc5_claim_extractor
        self._rc6_gap_analyzer = rc6_gap_analyzer
        self._gap_analysis_config = gap_analysis_config
        self._synthesizer = synthesizer
        self._clock: Callable[[], datetime] = clock if clock is not None else _utc_now

    def run(self, request: ResearchRequest) -> ResearchResult:  # noqa: C901
        """Execute the research pipeline for *request*.

        Returns a ResearchResult. Failures at recoverable stages return
        status=PARTIAL instead of raising. Failures that prevent any useful
        output raise typed exceptions.

        Raises:
            UnknownProfileError: if request.profiles contains an unresolvable ID.
            ProviderExecutionError: if no evidence could be retrieved from any
                configured provider.
            IncompleteResearchError: if request.strict is True and the result
                would be PARTIAL.
        """
        clock = self._clock
        events: list[TraceEvent] = []
        evt_count = 0

        def _emit(
            stage: TraceStage,
            status: TraceEventStatus,
            message: str,
        ) -> None:
            nonlocal evt_count
            evt_count += 1
            events.append(
                TraceEvent(
                    event_id=f"evt-{evt_count:04d}",
                    stage=stage,
                    status=status,
                    message=message,
                    occurred_at=clock(),
                )
            )

        # --- 1. REQUEST VALIDATION / INIT ---
        _emit(TraceStage.INIT, TraceEventStatus.STARTED, "Research engine starting.")

        # --- 2. PROFILE RESOLUTION ---
        if request.has_profiles:
            _emit(
                TraceStage.PROFILE_RESOLUTION,
                TraceEventStatus.STARTED,
                f"Resolving {len(request.profiles)} profile(s).",
            )
            if self._profile_provider is None:
                _emit(
                    TraceStage.PROFILE_RESOLUTION,
                    TraceEventStatus.FAILED,
                    "Profiles requested but no ProfileProvider is configured.",
                )
                raise ProviderExecutionError(
                    "ResearchRequest specifies profiles but no ProfileProvider was supplied "
                    "to ResearchEngine."
                )
            try:
                self._profile_provider.resolve_many(request.profiles)
                _emit(
                    TraceStage.PROFILE_RESOLUTION,
                    TraceEventStatus.COMPLETED,
                    f"Resolved {len(request.profiles)} profile(s).",
                )
            except UnknownProfileError:
                _emit(
                    TraceStage.PROFILE_RESOLUTION,
                    TraceEventStatus.FAILED,
                    "One or more profile IDs could not be resolved.",
                )
                raise
        else:
            _emit(
                TraceStage.PROFILE_RESOLUTION,
                TraceEventStatus.SKIPPED,
                "No profiles specified; profile resolution skipped.",
            )

        # --- 3 & 4. KNOWLEDGE RETRIEVAL + WEB RETRIEVAL ---
        raw_sources: list[Source] = []
        raw_evidence: list[EvidenceItem] = []
        partial = False

        if self._knowledge_provider is not None:
            _emit(
                TraceStage.RETRIEVAL,
                TraceEventStatus.STARTED,
                "Starting knowledge retrieval.",
            )
            try:
                kr = KnowledgeRetrievalRequest(
                    query=request.question,
                    parent_request=request,
                )
                k_result = self._knowledge_provider.retrieve(kr)
                raw_sources.extend(k_result.sources)
                raw_evidence.extend(k_result.evidence)
                _emit(
                    TraceStage.RETRIEVAL,
                    TraceEventStatus.COMPLETED,
                    (
                        f"Knowledge retrieval: {len(k_result.evidence)} item(s) "
                        f"from {len(k_result.sources)} source(s)."
                    ),
                )
            except Exception:
                _emit(
                    TraceStage.RETRIEVAL,
                    TraceEventStatus.FAILED,
                    "Knowledge retrieval failed.",
                )
                partial = True
        else:
            _emit(
                TraceStage.RETRIEVAL,
                TraceEventStatus.SKIPPED,
                "Knowledge retrieval skipped (no provider configured).",
            )

        if not request.use_web:
            _emit(
                TraceStage.RETRIEVAL,
                TraceEventStatus.SKIPPED,
                "Web retrieval skipped (not requested).",
            )
        elif self._web_search_provider is None:
            _emit(
                TraceStage.RETRIEVAL,
                TraceEventStatus.SKIPPED,
                "Web retrieval skipped (no provider configured).",
            )
        else:
            _emit(
                TraceStage.RETRIEVAL,
                TraceEventStatus.STARTED,
                "Starting web retrieval.",
            )
            try:
                ws_req = WebSearchRequest(
                    query=request.question,
                    parent_request=request,
                )
                w_result = self._web_search_provider.search(ws_req)
                raw_sources.extend(w_result.sources)
                raw_evidence.extend(w_result.evidence)
                _emit(
                    TraceStage.RETRIEVAL,
                    TraceEventStatus.COMPLETED,
                    (
                        f"Web retrieval: {len(w_result.evidence)} item(s) "
                        f"from {len(w_result.sources)} source(s)."
                    ),
                )
            except Exception:
                _emit(
                    TraceStage.RETRIEVAL,
                    TraceEventStatus.FAILED,
                    "Web retrieval failed.",
                )
                partial = True

        # Deduplicate sources and evidence by ID (preserve first-occurrence order)
        seen_src: set[str] = set()
        deduped_sources: list[Source] = []
        for s in raw_sources:
            if s.source_id not in seen_src:
                seen_src.add(s.source_id)
                deduped_sources.append(s)

        seen_ev: set[str] = set()
        deduped_evidence: list[EvidenceItem] = []
        for ev in raw_evidence:
            if ev.evidence_id not in seen_ev:
                seen_ev.add(ev.evidence_id)
                deduped_evidence.append(ev)

        sources: tuple[Source, ...] = tuple(deduped_sources)
        evidence: tuple[EvidenceItem, ...] = tuple(deduped_evidence)

        if not evidence:
            _emit(
                TraceStage.FINALIZATION,
                TraceEventStatus.FAILED,
                "No evidence retrieved. Cannot produce a meaningful result.",
            )
            raise ProviderExecutionError(
                "No evidence was retrieved from any configured provider. "
                "Increase retrieval scope or check provider configuration."
            )

        # --- 5. NORMALIZATION (RC4) ---
        from research_core.normalization.contracts import EvidenceRankingResult, RankedEvidence
        ranked_evidence: tuple[RankedEvidence, ...] = ()
        ranking_result: EvidenceRankingResult | None = None
        if self._evidence_normalizer is not None and self._evidence_ranker is not None:
            _emit(
                TraceStage.NORMALIZATION,
                TraceEventStatus.STARTED,
                f"Normalizing {len(evidence)} evidence item(s).",
            )
            try:
                normalized = self._evidence_normalizer.normalize(
                    sources=sources, evidence=evidence
                )
                _emit(
                    TraceStage.NORMALIZATION,
                    TraceEventStatus.COMPLETED,
                    f"Normalization: {len(normalized)} item(s) normalized.",
                )

                # --- 6. RANKING (RC4) ---
                _emit(
                    TraceStage.RANKING,
                    TraceEventStatus.STARTED,
                    f"Ranking {len(normalized)} normalized evidence item(s).",
                )
                ranking_result = self._evidence_ranker.rank(normalized)
                ranked_evidence = ranking_result.ranked
                _emit(
                    TraceStage.RANKING,
                    TraceEventStatus.COMPLETED,
                    f"Ranking: {len(ranked_evidence)} item(s) ranked.",
                )
            except Exception:
                _emit(
                    TraceStage.NORMALIZATION,
                    TraceEventStatus.FAILED,
                    "Normalization/ranking failed.",
                )
                partial = True
        else:
            _emit(
                TraceStage.NORMALIZATION,
                TraceEventStatus.SKIPPED,
                "Normalization skipped (no normalizer/ranker configured).",
            )
            _emit(
                TraceStage.RANKING,
                TraceEventStatus.SKIPPED,
                "Ranking skipped (no normalizer/ranker configured).",
            )

        # --- 7. CLAIM EXTRACTION ---
        from research_core.claims.contracts import ExtractedClaim
        claims: tuple[Claim, ...] = ()
        extracted_claims: tuple[ExtractedClaim, ...] = ()

        # RC5 path (preferred when available + ranked evidence present)
        if self._rc5_claim_extractor is not None and ranked_evidence:
            _emit(
                TraceStage.EXTRACTION,
                TraceEventStatus.STARTED,
                "Extracting claims from ranked evidence (RC5).",
            )
            try:
                extraction_result = self._rc5_claim_extractor.extract(ranked_evidence)
                extracted_claims = tuple(extraction_result.claims)
                # Bridge: wrap ExtractedClaim into legacy Claim for result.claims
                claims = tuple(
                    Claim(
                        claim_id=ec.claim_id,
                        statement=ec.claim_text,
                        supporting_evidence_ids=(ec.evidence_id,),
                    )
                    for ec in extracted_claims
                )
                _emit(
                    TraceStage.EXTRACTION,
                    TraceEventStatus.COMPLETED,
                    f"RC5 claim extraction: {len(extracted_claims)} claim(s) extracted.",
                )
            except Exception:
                _emit(
                    TraceStage.EXTRACTION,
                    TraceEventStatus.FAILED,
                    "RC5 claim extraction failed.",
                )
                partial = True
        # Legacy path
        elif self._claim_extractor is not None:
            _emit(
                TraceStage.EXTRACTION,
                TraceEventStatus.STARTED,
                "Extracting claims from evidence.",
            )
            try:
                claims = self._claim_extractor.extract(evidence, request)
                _emit(
                    TraceStage.EXTRACTION,
                    TraceEventStatus.COMPLETED,
                    f"Claim extraction: {len(claims)} claim(s) extracted.",
                )
            except Exception:
                _emit(
                    TraceStage.EXTRACTION,
                    TraceEventStatus.FAILED,
                    "Claim extraction failed.",
                )
                partial = True
        else:
            _emit(
                TraceStage.EXTRACTION,
                TraceEventStatus.SKIPPED,
                "Claim extraction skipped (no extractor configured).",
            )

        # --- CONTRADICTION DETECTION (legacy only, no-op in RC7 new pipeline) ---
        contradictions: tuple[Contradiction, ...] = ()
        if self._contradiction_detector is not None:
            _emit(
                TraceStage.CONTRADICTION_DETECTION,
                TraceEventStatus.STARTED,
                "Detecting contradictions.",
            )
            try:
                contradictions = self._contradiction_detector.detect(
                    claims, evidence, request
                )
                _emit(
                    TraceStage.CONTRADICTION_DETECTION,
                    TraceEventStatus.COMPLETED,
                    f"Contradiction detection: {len(contradictions)} contradiction(s).",
                )
            except Exception:
                _emit(
                    TraceStage.CONTRADICTION_DETECTION,
                    TraceEventStatus.FAILED,
                    "Contradiction detection failed.",
                )
                partial = True
        else:
            _emit(
                TraceStage.CONTRADICTION_DETECTION,
                TraceEventStatus.SKIPPED,
                "Contradiction detection skipped (no detector configured).",
            )

        # --- 8. GAP ANALYSIS ---
        from research_core.analysis.contracts import GapAnalysisResult
        gaps: tuple[ResearchGap, ...] = ()
        open_questions: tuple[OpenQuestion, ...] = ()
        gap_analysis_result: GapAnalysisResult | None = None

        # RC6 path (preferred when available + ranked evidence present)
        if self._rc6_gap_analyzer is not None and ranked_evidence:
            _emit(
                TraceStage.GAP_ANALYSIS,
                TraceEventStatus.STARTED,
                "Analyzing research gaps (RC6).",
            )
            try:
                gap_analysis_result = self._rc6_gap_analyzer.analyze(
                    sources, ranked_evidence, extracted_claims, ranking_result,
                    self._gap_analysis_config if self._gap_analysis_config is not None
                    else GapAnalysisConfig(),
                )
                gaps = gap_analysis_result.gaps
                # RC6 recommended_status is authoritative
                if gap_analysis_result.recommended_status == ResearchStatus.PARTIAL:
                    partial = True
                _emit(
                    TraceStage.GAP_ANALYSIS,
                    TraceEventStatus.COMPLETED,
                    (
                        f"RC6 gap analysis: {len(gaps)} gap(s). "
                        f"Recommended: {gap_analysis_result.recommended_status.value}."
                    ),
                )
            except Exception:
                _emit(
                    TraceStage.GAP_ANALYSIS,
                    TraceEventStatus.FAILED,
                    "RC6 gap analysis failed.",
                )
                partial = True
        # Legacy path
        elif self._gap_analyzer is not None:
            _emit(
                TraceStage.GAP_ANALYSIS,
                TraceEventStatus.STARTED,
                "Analyzing research gaps.",
            )
            try:
                gaps, open_questions = self._gap_analyzer.analyze(
                    claims, evidence, contradictions, request
                )
                _emit(
                    TraceStage.GAP_ANALYSIS,
                    TraceEventStatus.COMPLETED,
                    (
                        f"Gap analysis: {len(gaps)} gap(s), "
                        f"{len(open_questions)} open question(s)."
                    ),
                )
            except Exception:
                _emit(
                    TraceStage.GAP_ANALYSIS,
                    TraceEventStatus.FAILED,
                    "Gap analysis failed.",
                )
                partial = True
        else:
            _emit(
                TraceStage.GAP_ANALYSIS,
                TraceEventStatus.SKIPPED,
                "Gap analysis skipped (no analyzer configured).",
            )

        # --- 9. SYNTHESIS ---
        synthesis: SynthesisResult | None = None
        if self._synthesizer is not None:
            _emit(
                TraceStage.SYNTHESIS,
                TraceEventStatus.STARTED,
                "Starting synthesis.",
            )
            try:
                synthesis_input = SynthesisInput(
                    request_text=request.question,
                    sources=sources,
                    evidence=ranked_evidence,
                    claims=extracted_claims,
                    gap_analysis=gap_analysis_result,
                )
                synthesis = self._synthesizer.synthesize(synthesis_input)
                _emit(
                    TraceStage.SYNTHESIS,
                    TraceEventStatus.COMPLETED,
                    "Synthesis completed.",
                )
            except Exception:
                _emit(
                    TraceStage.SYNTHESIS,
                    TraceEventStatus.FAILED,
                    "Synthesis failed; result will be partial.",
                )
                partial = True
        else:
            _emit(
                TraceStage.SYNTHESIS,
                TraceEventStatus.SKIPPED,
                "Synthesis skipped (no synthesizer configured).",
            )

        # --- QUALITY COMPUTATION ---
        # Use RC6 quality when available; fall back to legacy evidence-signal quality.
        quality: QualityDiagnostics | None = None
        if gap_analysis_result is None:
            quality = _compute_quality(evidence)

        # --- STATUS DETERMINATION ---
        if not evidence:
            partial = True

        status = ResearchStatus.PARTIAL if partial else ResearchStatus.COMPLETE

        if request.strict and status == ResearchStatus.PARTIAL:
            raise IncompleteResearchError(
                "Research result is incomplete and strict mode is enabled. "
                "Disable strict mode to receive a partial result."
            )

        # --- 10. RESULT ASSEMBLY / FINALIZATION ---
        _emit(
            TraceStage.FINALIZATION,
            TraceEventStatus.COMPLETED,
            (
                f"Research finalized. Status: {status}. "
                f"Sources: {len(sources)}, evidence: {len(evidence)}, "
                f"claims: {len(claims)}, gaps: {len(gaps)}."
            ),
        )

        trace = ResearchTrace(events=tuple(events))

        return ResearchResult(
            request=request,
            status=status,
            sources=sources,
            evidence=evidence,
            claims=claims,
            contradictions=contradictions,
            gaps=gaps,
            open_questions=open_questions,
            synthesis=synthesis,
            quality=quality,
            trace=trace,
            completed_at=clock(),
            ranked_evidence=ranked_evidence,
            gap_analysis=gap_analysis_result,
        )
