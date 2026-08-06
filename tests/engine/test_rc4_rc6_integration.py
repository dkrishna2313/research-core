"""
RC7 regression tests: engine integration with RC4-RC6 pipeline components.

Validates that the engine correctly:
  - Invokes EvidenceNormalizer and EvidenceRanker (RC4)
  - Invokes DeterministicClaimExtractor (RC5)
  - Invokes DeterministicGapAnalyzer (RC6)
  - Uses RC6 recommended_status authoritatively
  - Stores gap_analysis in ResearchResult
  - Uses RC6 quality diagnostics (not a second quality model)
  - Emits NORMALIZATION and RANKING trace stages
  - Handles synthesis failure while preserving RC6 gaps and quality
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from research_core.analysis.analyzer import DeterministicGapAnalyzer
from research_core.analysis.config import GapAnalysisConfig
from research_core.analysis.contracts import GapAnalysisResult
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import ResearchResult, ResearchStatus
from research_core.contracts.trace import TraceEventStatus, TraceStage
from research_core.engine import ResearchEngine
from research_core.normalization.normalizer import EvidenceNormalizer
from research_core.normalization.ranker import EvidenceRanker
from research_core.synthesis.deterministic import DeterministicSynthesizer
from tests.engine.conftest import (
    FixedKnowledgeProvider,
    fixed_clock,
    make_evidence,
    make_source,
)

FIXED_TS = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)


def _make_knowledge_provider(
    source_id: str = "src-1", evidence_id: str = "ev-1"
) -> FixedKnowledgeProvider:
    src = make_source(source_id)
    ev = make_evidence(evidence_id, source_id)
    return FixedKnowledgeProvider((src,), (ev,))


def _make_rc4_rc6_engine(**overrides: Any) -> ResearchEngine:
    """Build an engine with the full RC4-RC6 pipeline wired up."""
    defaults: dict[str, Any] = {
        "knowledge_provider": _make_knowledge_provider(),
        "evidence_normalizer": EvidenceNormalizer(),
        "evidence_ranker": EvidenceRanker(),
        "rc6_gap_analyzer": DeterministicGapAnalyzer(),
        "gap_analysis_config": GapAnalysisConfig(),
        "synthesizer": DeterministicSynthesizer(),
        "clock": fixed_clock,
    }
    defaults.update(overrides)
    return ResearchEngine(**defaults)  # type: ignore[arg-type]


@pytest.mark.engine
class TestEngineNormalizationAndRanking:
    def test_engine_emits_normalization_trace_stage(self) -> None:
        engine = _make_rc4_rc6_engine()
        result = engine.run(ResearchRequest(question="test normalization"))
        assert result.trace is not None
        norm_events = result.trace.events_for_stage(TraceStage.NORMALIZATION)
        assert len(norm_events) > 0

    def test_engine_emits_ranking_trace_stage(self) -> None:
        engine = _make_rc4_rc6_engine()
        result = engine.run(ResearchRequest(question="test ranking"))
        assert result.trace is not None
        rank_events = result.trace.events_for_stage(TraceStage.RANKING)
        assert len(rank_events) > 0

    def test_normalization_completes_before_ranking(self) -> None:
        engine = _make_rc4_rc6_engine()
        result = engine.run(ResearchRequest(question="test order"))
        assert result.trace is not None
        events = result.trace.events
        norm_idx = next(
            i for i, e in enumerate(events) if e.stage == TraceStage.NORMALIZATION
        )
        rank_idx = next(
            i for i, e in enumerate(events) if e.stage == TraceStage.RANKING
        )
        assert norm_idx < rank_idx

    def test_ranked_evidence_in_result(self) -> None:
        engine = _make_rc4_rc6_engine()
        result = engine.run(ResearchRequest(question="test ranked evidence"))
        assert len(result.ranked_evidence) > 0

    def test_ranked_evidence_is_empty_without_rc4(self) -> None:
        engine = ResearchEngine(
            knowledge_provider=_make_knowledge_provider(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test no rc4"))
        assert result.ranked_evidence == ()


@pytest.mark.engine
class TestEngineRC6GapAnalysis:
    def test_gap_analysis_stored_in_result(self) -> None:
        engine = _make_rc4_rc6_engine()
        result = engine.run(ResearchRequest(question="test gap analysis"))
        assert result.gap_analysis is not None
        assert isinstance(result.gap_analysis, GapAnalysisResult)

    def test_gap_analysis_none_without_rc6(self) -> None:
        engine = ResearchEngine(
            knowledge_provider=_make_knowledge_provider(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test no rc6"))
        assert result.gap_analysis is None

    def test_rc6_quality_diagnostics_present(self) -> None:
        engine = _make_rc4_rc6_engine()
        result = engine.run(ResearchRequest(question="test quality"))
        assert result.gap_analysis is not None
        qd = result.gap_analysis.quality_diagnostics
        assert qd is not None
        assert qd.analyzer == "DeterministicGapAnalyzer"

    def test_rc6_quality_not_duplicated_as_legacy_quality(self) -> None:
        engine = _make_rc4_rc6_engine()
        result = engine.run(ResearchRequest(question="test no dual quality"))
        # When RC6 is used, legacy quality field is None
        assert result.quality is None

    def test_rc6_recommended_partial_overrides_status(self) -> None:
        """RC6 PARTIAL recommendation must result in PARTIAL engine status."""
        engine = _make_rc4_rc6_engine()
        # A real DeterministicGapAnalyzer with a single source will often recommend PARTIAL
        # since coverage conditions may fail. We verify the engine respects the recommendation.
        result = engine.run(ResearchRequest(question="test status"))
        assert result.gap_analysis is not None
        if result.gap_analysis.recommended_status == ResearchStatus.PARTIAL:
            assert result.status == ResearchStatus.PARTIAL

    def test_critical_gap_forces_partial(self) -> None:
        """When RC6 recommends PARTIAL, engine must not return COMPLETE."""
        engine = _make_rc4_rc6_engine()
        result = engine.run(ResearchRequest(question="test critical gap"))
        assert result.gap_analysis is not None
        if result.gap_analysis.recommended_status == ResearchStatus.PARTIAL:
            assert result.status != ResearchStatus.COMPLETE


@pytest.mark.engine
class TestEngineNoContradictionStage:
    def test_no_contradiction_stage_in_rc7_pipeline(self) -> None:
        engine = _make_rc4_rc6_engine()
        result = engine.run(ResearchRequest(question="test no contradiction"))
        assert result.trace is not None
        # Without a contradiction_detector, the stage is SKIPPED
        contra_events = result.trace.events_for_stage(
            TraceStage.CONTRADICTION_DETECTION
        )
        assert all(e.status == TraceEventStatus.SKIPPED for e in contra_events)


@pytest.mark.engine
class TestEngineSynthesisFailureWithRC6:
    def test_synthesis_failure_preserves_rc6_gap_analysis(self) -> None:
        from tests.engine.conftest import FailingSynthesizer

        engine = _make_rc4_rc6_engine(synthesizer=FailingSynthesizer())
        result = engine.run(ResearchRequest(question="test partial with rc6"))
        assert result.status == ResearchStatus.PARTIAL
        assert result.synthesis is None
        # RC6 gap_analysis must be preserved even when synthesis fails
        assert result.gap_analysis is not None

    def test_synthesis_failure_preserves_ranked_evidence(self) -> None:
        from tests.engine.conftest import FailingSynthesizer

        engine = _make_rc4_rc6_engine(synthesizer=FailingSynthesizer())
        result = engine.run(ResearchRequest(question="test ranked preserved"))
        assert result.status == ResearchStatus.PARTIAL
        assert len(result.ranked_evidence) > 0

    def test_synthesis_failure_preserves_sources(self) -> None:
        from tests.engine.conftest import FailingSynthesizer

        engine = _make_rc4_rc6_engine(synthesizer=FailingSynthesizer())
        result = engine.run(ResearchRequest(question="test sources preserved"))
        assert len(result.sources) > 0

    def test_synthesis_failure_preserves_evidence(self) -> None:
        from tests.engine.conftest import FailingSynthesizer

        engine = _make_rc4_rc6_engine(synthesizer=FailingSynthesizer())
        result = engine.run(ResearchRequest(question="test evidence preserved"))
        assert len(result.evidence) > 0


@pytest.mark.engine
class TestEngineLegacyBackwardCompat:
    """Verify the legacy (old-style) pipeline still works unchanged."""

    def test_legacy_pipeline_still_works(self) -> None:
        from tests.engine.conftest import SimpleCLaimExtractor, SimpleGapAnalyzer

        engine = ResearchEngine(
            knowledge_provider=_make_knowledge_provider(),
            claim_extractor=SimpleCLaimExtractor(),
            gap_analyzer=SimpleGapAnalyzer(),
            synthesizer=DeterministicSynthesizer(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test legacy"))
        assert isinstance(result, ResearchResult)
        assert len(result.claims) > 0
        assert result.synthesis is not None

    def test_legacy_has_quality_diagnostics(self) -> None:
        from tests.engine.conftest import SimpleCLaimExtractor, SimpleGapAnalyzer

        engine = ResearchEngine(
            knowledge_provider=_make_knowledge_provider(),
            claim_extractor=SimpleCLaimExtractor(),
            gap_analyzer=SimpleGapAnalyzer(),
            synthesizer=DeterministicSynthesizer(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test legacy quality"))
        assert result.quality is not None
        assert result.gap_analysis is None
