"""
ResearchEngine — end-to-end research pipeline orchestration.

The engine coordinates provider calls and analysis stages without embedding
their logic. All stage implementations are injected; the engine is domain-neutral
and provider-neutral.

Stage order:
  1. INIT
  2. PROFILE_RESOLUTION
  3. RETRIEVAL (knowledge, then web)
  4. EXTRACTION (claims)
  5. CONTRADICTION_DETECTION
  6. GAP_ANALYSIS
  7. SYNTHESIS
  8. FINALIZATION

Partial-result semantics:
  - Failures that prevent any meaningful result raise typed exceptions.
  - Failures after useful evidence is produced return
    ResearchResult(status=PARTIAL) with all available artifacts preserved.
  - Empty evidence never yields COMPLETE status.
  - Synthesis failure preserves all prior artifacts and returns PARTIAL.
  - strict=True raises IncompleteResearchError instead of returning PARTIAL.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

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
from research_core.protocols.synthesis import Synthesizer
from research_core.protocols.web import WebSearchProvider, WebSearchRequest


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _compute_quality(evidence: tuple[EvidenceItem, ...]) -> QualityDiagnostics:
    """Compute aggregate QualityDiagnostics from evidence item quality signals."""
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

    Dependencies (all optional unless noted):
        profile_provider:       resolves profile IDs in the request (required if
                                request.profiles is non-empty)
        knowledge_provider:     retrieves evidence from a local knowledge store
        web_search_provider:    retrieves evidence from web search
        claim_extractor:        extracts Claim objects from evidence
        contradiction_detector: detects Contradiction objects across claims/evidence
        gap_analyzer:           identifies ResearchGap and OpenQuestion objects
        synthesizer:            produces a SynthesisResult from analysis outputs
        clock:                  callable returning timezone-aware datetime; defaults
                                to datetime.now(UTC) — override in tests for
                                deterministic trace timestamps
    """

    def __init__(
        self,
        *,
        profile_provider: ProfileProvider | None = None,
        knowledge_provider: KnowledgeProvider | None = None,
        web_search_provider: WebSearchProvider | None = None,
        claim_extractor: ClaimExtractor | None = None,
        contradiction_detector: ContradictionDetector | None = None,
        gap_analyzer: GapAnalyzer | None = None,
        synthesizer: Synthesizer | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._profile_provider = profile_provider
        self._knowledge_provider = knowledge_provider
        self._web_search_provider = web_search_provider
        self._claim_extractor = claim_extractor
        self._contradiction_detector = contradiction_detector
        self._gap_analyzer = gap_analyzer
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

        # --- 1. INIT ---
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

        # --- 3. RETRIEVAL ---
        raw_sources: list[Source] = []
        raw_evidence: list[EvidenceItem] = []
        partial = False

        # Knowledge retrieval
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

        # Web retrieval
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

        # No evidence at all — no useful output, raise
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

        # --- 4. CLAIM EXTRACTION ---
        claims: tuple[Claim, ...] = ()
        if self._claim_extractor is not None:
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

        # --- 5. CONTRADICTION DETECTION ---
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

        # --- 6. GAP ANALYSIS ---
        gaps: tuple[ResearchGap, ...] = ()
        open_questions: tuple[OpenQuestion, ...] = ()
        if self._gap_analyzer is not None:
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

        # --- 7. SYNTHESIS ---
        synthesis: SynthesisResult | None = None
        if self._synthesizer is not None:
            _emit(
                TraceStage.SYNTHESIS,
                TraceEventStatus.STARTED,
                "Starting synthesis.",
            )
            try:
                synthesis = self._synthesizer.synthesize(
                    request,
                    evidence,
                    claims,
                    contradictions,
                    gaps,
                    open_questions,
                )
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
                # synthesis remains None; all prior artifacts are preserved
        else:
            _emit(
                TraceStage.SYNTHESIS,
                TraceEventStatus.SKIPPED,
                "Synthesis skipped (no synthesizer configured).",
            )

        # --- 8. QUALITY COMPUTATION ---
        quality = _compute_quality(evidence)

        # --- STATUS DETERMINATION ---
        # Empty evidence is never COMPLETE (already raised above if no evidence,
        # but guard here in case logic changes).
        if not evidence:
            partial = True

        status = ResearchStatus.PARTIAL if partial else ResearchStatus.COMPLETE

        # Strict mode: raise instead of returning PARTIAL
        if request.strict and status == ResearchStatus.PARTIAL:
            raise IncompleteResearchError(
                "Research result is incomplete and strict mode is enabled. "
                "Disable strict mode to receive a partial result."
            )

        # --- FINALIZATION ---
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
        )
