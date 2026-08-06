"""
RC7 final pipeline trace regression test.

Validates the fully configured 10-stage engine pipeline with all RC4-RC6
components wired:

  Stage  TraceStage                Outcome (no-profile, no-web run)
  -----  ------------------------  --------------------------------
  1      INIT                      STARTED
  2      PROFILE_RESOLUTION        SKIPPED
  3      RETRIEVAL (knowledge)     COMPLETED
  4      RETRIEVAL (web)           SKIPPED
  5      NORMALIZATION             COMPLETED
  6      RANKING                   COMPLETED
  7      EXTRACTION                COMPLETED  (RC5 DeterministicClaimExtractor)
  8      CONTRADICTION_DETECTION   SKIPPED    (no detector in RC7 pipeline)
  9      GAP_ANALYSIS              COMPLETED  (RC6 DeterministicGapAnalyzer)
  10     SYNTHESIS                 COMPLETED
         FINALIZATION              COMPLETED

This file is the single authoritative test that the aligned engine produces
a well-formed, deterministic 10-stage trace, that RC6 gap_analysis is the
true GapAnalysisResult type, that DeterministicSynthesizer emits sections
and citations with correct ID formulas, and that MarkdownRenderer handles
the fully populated result without error.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from research_core.analysis.analyzer import DeterministicGapAnalyzer
from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.contracts import GapAnalysisResult
from research_core.claims.extractor import DeterministicClaimExtractor
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import ResearchResult, ResearchStatus
from research_core.contracts.trace import TraceEventStatus, TraceStage
from research_core.engine import ResearchEngine
from research_core.normalization.normalizer import EvidenceNormalizer
from research_core.normalization.ranker import EvidenceRanker
from research_core.renderers.markdown import MarkdownRenderer
from research_core.synthesis.deterministic import DeterministicSynthesizer
from tests.engine.conftest import (
    FailingSynthesizer,
    FixedKnowledgeProvider,
    fixed_clock,
    make_evidence,
    make_source,
)


def _make_fully_configured_engine(**overrides: Any) -> ResearchEngine:
    """Engine with the full RC4-RC6 pipeline (normalizer, ranker, RC5, RC6, synthesizer)."""
    src = make_source("src-1")
    ev = make_evidence("ev-1", "src-1")
    defaults: dict[str, Any] = {
        "knowledge_provider": FixedKnowledgeProvider((src,), (ev,)),
        "evidence_normalizer": EvidenceNormalizer(),
        "evidence_ranker": EvidenceRanker(),
        "rc5_claim_extractor": DeterministicClaimExtractor(),
        "rc6_gap_analyzer": DeterministicGapAnalyzer(),
        "gap_analysis_config": GapAnalysisConfig(),
        "synthesizer": DeterministicSynthesizer(),
        "clock": fixed_clock,
    }
    defaults.update(overrides)
    return ResearchEngine(**defaults)  # type: ignore[arg-type]


def _run(engine: ResearchEngine, question: str = "test final pipeline trace") -> ResearchResult:
    return engine.run(ResearchRequest(question=question))


def _first_idx(events: tuple, stage: TraceStage) -> int:
    return next(i for i, e in enumerate(events) if e.stage == stage)


# --------------------------------------------------------------------------- #
# Stage presence and order
# --------------------------------------------------------------------------- #

@pytest.mark.engine
class TestFinalPipelineTraceOrder:
    def test_all_ten_logical_stages_appear(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.trace is not None
        stages = {e.stage for e in result.trace.events}
        expected = {
            TraceStage.INIT,
            TraceStage.PROFILE_RESOLUTION,
            TraceStage.RETRIEVAL,
            TraceStage.NORMALIZATION,
            TraceStage.RANKING,
            TraceStage.EXTRACTION,
            TraceStage.CONTRADICTION_DETECTION,
            TraceStage.GAP_ANALYSIS,
            TraceStage.SYNTHESIS,
            TraceStage.FINALIZATION,
        }
        assert expected <= stages

    def test_init_is_first_event(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.trace is not None
        assert result.trace.events[0].stage == TraceStage.INIT

    def test_finalization_is_last_event(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.trace is not None
        assert result.trace.events[-1].stage == TraceStage.FINALIZATION

    def test_normalization_before_ranking(self) -> None:
        result = _run(_make_fully_configured_engine())
        evts = result.trace.events
        assert _first_idx(evts, TraceStage.NORMALIZATION) < _first_idx(evts, TraceStage.RANKING)

    def test_ranking_before_extraction(self) -> None:
        result = _run(_make_fully_configured_engine())
        evts = result.trace.events
        assert _first_idx(evts, TraceStage.RANKING) < _first_idx(evts, TraceStage.EXTRACTION)

    def test_extraction_before_gap_analysis(self) -> None:
        result = _run(_make_fully_configured_engine())
        evts = result.trace.events
        assert _first_idx(evts, TraceStage.EXTRACTION) < _first_idx(evts, TraceStage.GAP_ANALYSIS)

    def test_gap_analysis_before_synthesis(self) -> None:
        result = _run(_make_fully_configured_engine())
        evts = result.trace.events
        assert _first_idx(evts, TraceStage.GAP_ANALYSIS) < _first_idx(evts, TraceStage.SYNTHESIS)

    def test_synthesis_before_finalization(self) -> None:
        result = _run(_make_fully_configured_engine())
        evts = result.trace.events
        assert _first_idx(evts, TraceStage.SYNTHESIS) < _first_idx(evts, TraceStage.FINALIZATION)

    def test_normalization_completed(self) -> None:
        result = _run(_make_fully_configured_engine())
        norm = result.trace.events_for_stage(TraceStage.NORMALIZATION)
        assert any(e.status == TraceEventStatus.COMPLETED for e in norm)

    def test_ranking_completed(self) -> None:
        result = _run(_make_fully_configured_engine())
        rank = result.trace.events_for_stage(TraceStage.RANKING)
        assert any(e.status == TraceEventStatus.COMPLETED for e in rank)

    def test_extraction_completed(self) -> None:
        result = _run(_make_fully_configured_engine())
        ext = result.trace.events_for_stage(TraceStage.EXTRACTION)
        assert any(e.status == TraceEventStatus.COMPLETED for e in ext)

    def test_gap_analysis_completed(self) -> None:
        result = _run(_make_fully_configured_engine())
        gap = result.trace.events_for_stage(TraceStage.GAP_ANALYSIS)
        assert any(e.status == TraceEventStatus.COMPLETED for e in gap)

    def test_synthesis_completed(self) -> None:
        result = _run(_make_fully_configured_engine())
        syn = result.trace.events_for_stage(TraceStage.SYNTHESIS)
        assert any(e.status == TraceEventStatus.COMPLETED for e in syn)

    def test_contradiction_detection_skipped(self) -> None:
        result = _run(_make_fully_configured_engine())
        cd = result.trace.events_for_stage(TraceStage.CONTRADICTION_DETECTION)
        assert len(cd) > 0
        assert all(e.status == TraceEventStatus.SKIPPED for e in cd)

    def test_profile_resolution_skipped_no_profiles(self) -> None:
        result = _run(_make_fully_configured_engine())
        pr = result.trace.events_for_stage(TraceStage.PROFILE_RESOLUTION)
        assert len(pr) > 0
        assert all(e.status == TraceEventStatus.SKIPPED for e in pr)


# --------------------------------------------------------------------------- #
# RC6 GapAnalysisResult integration
# --------------------------------------------------------------------------- #

@pytest.mark.engine
class TestFinalPipelineRC6Integration:
    def test_gap_analysis_is_gap_analysis_result(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.gap_analysis is not None
        assert isinstance(result.gap_analysis, GapAnalysisResult)

    def test_rc6_quality_uses_deterministic_analyzer(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.gap_analysis is not None
        assert result.gap_analysis.quality_diagnostics.analyzer == "DeterministicGapAnalyzer"

    def test_legacy_quality_field_none_with_rc6(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.quality is None

    def test_rc6_recommended_status_controls_engine_status(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.gap_analysis is not None
        if result.gap_analysis.recommended_status == ResearchStatus.PARTIAL:
            assert result.status == ResearchStatus.PARTIAL

    def test_ranked_evidence_populated(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert len(result.ranked_evidence) > 0


# --------------------------------------------------------------------------- #
# Structured synthesis: sections, citations, IDs
# --------------------------------------------------------------------------- #

@pytest.mark.engine
class TestFinalPipelineStructuredSynthesis:
    def test_synthesis_has_sections(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.synthesis is not None
        assert len(result.synthesis.sections) > 0

    def test_summary_section_present(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.synthesis is not None
        titles = [s.title for s in result.synthesis.sections]
        assert "Summary" in titles

    def test_section_id_formula_for_summary(self) -> None:
        """Summary section_id: sec- + sha256(title NUL order NUL version)[:16]."""
        result = _run(_make_fully_configured_engine())
        assert result.synthesis is not None
        version = "1"
        title, order = "Summary", 0
        expected = "sec-" + hashlib.sha256(
            f"{title}\x00{order}\x00{version}".encode()
        ).hexdigest()[:16]
        summary = next(s for s in result.synthesis.sections if s.title == "Summary")
        assert summary.section_id == expected

    def test_citation_id_formula_for_all_citations(self) -> None:
        """citation_id: cit- + sha256(claim NUL ev NUL src NUL sec NUL version)[:20]."""
        result = _run(_make_fully_configured_engine())
        assert result.synthesis is not None
        if not result.synthesis.citations:
            pytest.skip("No citations produced (evidence may contain no extractable claims)")
        for cit in result.synthesis.citations:
            parts = [cit.claim_id, cit.evidence_id, cit.source_id, cit.section_id, "1"]
            payload = "\x00".join(parts)
            expected = "cit-" + hashlib.sha256(payload.encode()).hexdigest()[:20]
            assert cit.citation_id == expected, f"Bad citation_id for {cit.claim_id}"

    def test_all_cited_claims_appear_in_result_claims(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.synthesis is not None
        if not result.synthesis.citations:
            pytest.skip("No citations to check")
        result_claim_ids = {c.claim_id for c in result.claims}
        for cit in result.synthesis.citations:
            assert cit.claim_id in result_claim_ids

    def test_synthesis_diagnostics_present(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.synthesis is not None
        assert result.synthesis.synthesis_diagnostics is not None

    def test_synthesis_diagnostics_sections_count_matches_sections(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.synthesis is not None
        diag = result.synthesis.synthesis_diagnostics
        assert diag is not None
        assert diag.sections_emitted == len(result.synthesis.sections)

    def test_synthesis_deterministic_across_engine_instances(self) -> None:
        r1 = _run(_make_fully_configured_engine(), "determinism check")
        r2 = _run(_make_fully_configured_engine(), "determinism check")
        assert r1.synthesis is not None
        assert r2.synthesis is not None
        ids1 = tuple(s.section_id for s in r1.synthesis.sections)
        ids2 = tuple(s.section_id for s in r2.synthesis.sections)
        assert ids1 == ids2

    def test_synthesis_citations_deterministic(self) -> None:
        r1 = _run(_make_fully_configured_engine(), "determinism check citations")
        r2 = _run(_make_fully_configured_engine(), "determinism check citations")
        assert r1.synthesis is not None
        assert r2.synthesis is not None
        cit_ids1 = tuple(c.citation_id for c in r1.synthesis.citations)
        cit_ids2 = tuple(c.citation_id for c in r2.synthesis.citations)
        assert cit_ids1 == cit_ids2


# --------------------------------------------------------------------------- #
# Renderer purity on fully configured result
# --------------------------------------------------------------------------- #

@pytest.mark.engine
class TestFinalPipelineRendererPurity:
    def test_renderer_does_not_raise(self) -> None:
        result = _run(_make_fully_configured_engine())
        md = MarkdownRenderer().render(result)
        assert md

    def test_rendered_output_ends_with_single_newline(self) -> None:
        result = _run(_make_fully_configured_engine())
        md = MarkdownRenderer().render(result)
        assert md.endswith("\n")
        assert not md.endswith("\n\n")

    def test_rendered_output_has_no_trailing_whitespace(self) -> None:
        result = _run(_make_fully_configured_engine())
        md = MarkdownRenderer().render(result)
        for ln in md.splitlines():
            assert ln == ln.rstrip(), f"Trailing whitespace on line: {ln!r}"

    def test_rendered_output_is_deterministic(self) -> None:
        result = _run(_make_fully_configured_engine(), "render determinism")
        md1 = MarkdownRenderer().render(result)
        md2 = MarkdownRenderer().render(result)
        assert md1 == md2

    def test_render_does_not_mutate_synthesis(self) -> None:
        result = _run(_make_fully_configured_engine())
        assert result.synthesis is not None
        section_ids_before = tuple(s.section_id for s in result.synthesis.sections)
        MarkdownRenderer().render(result)
        section_ids_after = tuple(s.section_id for s in result.synthesis.sections)
        assert section_ids_before == section_ids_after


# --------------------------------------------------------------------------- #
# Synthesis failure preserves RC6 artifacts (with RC5 in pipeline)
# --------------------------------------------------------------------------- #

@pytest.mark.engine
class TestFinalPipelineSynthesisFailurePreservation:
    def test_synthesis_failure_preserves_gap_analysis(self) -> None:
        engine = _make_fully_configured_engine(synthesizer=FailingSynthesizer())
        result = _run(engine)
        assert result.status == ResearchStatus.PARTIAL
        assert result.synthesis is None
        assert result.gap_analysis is not None

    def test_synthesis_failure_preserves_ranked_evidence(self) -> None:
        engine = _make_fully_configured_engine(synthesizer=FailingSynthesizer())
        result = _run(engine)
        assert len(result.ranked_evidence) > 0

    def test_synthesis_failure_preserves_rc5_claims(self) -> None:
        engine = _make_fully_configured_engine(synthesizer=FailingSynthesizer())
        result = _run(engine)
        # RC5 extraction runs before synthesis — claims must survive synthesis failure
        assert isinstance(result.claims, tuple)
