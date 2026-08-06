"""
Tests for partial-result semantics, especially the mandatory synthesis-failure test.

Acceptance invariant: synthesis failure must return ResearchResult(status=PARTIAL),
preserve all prior artifacts, and not raise by default.
"""

from __future__ import annotations

import pytest

from research_core.contracts.result import ResearchResult, ResearchStatus
from research_core.contracts.serialization import serialize
from research_core.contracts.trace import TraceEventStatus, TraceStage
from research_core.engine import ResearchEngine
from tests.engine.conftest import (
    FailingClaimExtractor,
    FailingGapAnalyzer,
    FailingKnowledgeProvider,
    FailingSynthesizer,
    FailingWebProvider,
    FixedKnowledgeProvider,
    FixedWebProvider,
    SimpleCLaimExtractor,
    SimpleGapAnalyzer,
    fixed_clock,
    make_evidence,
    make_source,
)


@pytest.mark.engine
class TestSynthesisFailureReturnsPartial:
    """MANDATORY: synthesis failure must return PARTIAL, not raise."""

    def _make_engine_with_failing_synthesizer(self) -> ResearchEngine:
        src = make_source("src-1")
        ev = make_evidence("ev-1", "src-1", content="Climate change affects biodiversity.")
        return ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            claim_extractor=SimpleCLaimExtractor(),
            gap_analyzer=SimpleGapAnalyzer(),
            synthesizer=FailingSynthesizer(),
            clock=fixed_clock,
        )

    def test_synthesis_failure_does_not_raise(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine_with_failing_synthesizer()
        result = engine.run(ResearchRequest(question="test synthesis failure"))
        assert isinstance(result, ResearchResult)

    def test_synthesis_failure_returns_partial(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine_with_failing_synthesizer()
        result = engine.run(ResearchRequest(question="test synthesis failure"))
        assert result.status == ResearchStatus.PARTIAL

    def test_synthesis_failure_preserves_sources(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine_with_failing_synthesizer()
        result = engine.run(ResearchRequest(question="test synthesis failure"))
        assert len(result.sources) > 0

    def test_synthesis_failure_preserves_evidence(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine_with_failing_synthesizer()
        result = engine.run(ResearchRequest(question="test synthesis failure"))
        assert len(result.evidence) > 0

    def test_synthesis_failure_preserves_claims(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine_with_failing_synthesizer()
        result = engine.run(ResearchRequest(question="test synthesis failure"))
        assert len(result.claims) > 0

    def test_synthesis_failure_preserves_quality_diagnostics(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine_with_failing_synthesizer()
        result = engine.run(ResearchRequest(question="test synthesis failure"))
        assert result.quality is not None

    def test_synthesis_failure_preserves_trace(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine_with_failing_synthesizer()
        result = engine.run(ResearchRequest(question="test synthesis failure"))
        assert result.trace is not None
        assert len(result.trace.events) > 0

    def test_synthesis_failure_recorded_in_trace(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine_with_failing_synthesizer()
        result = engine.run(ResearchRequest(question="test synthesis failure"))
        assert result.trace is not None
        failed_synthesis = [
            e for e in result.trace.events
            if e.stage == TraceStage.SYNTHESIS and e.status == TraceEventStatus.FAILED
        ]
        assert len(failed_synthesis) == 1

    def test_synthesis_failure_synthesis_is_none(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine_with_failing_synthesizer()
        result = engine.run(ResearchRequest(question="test synthesis failure"))
        assert result.synthesis is None

    def test_synthesis_failure_result_serializes(self) -> None:
        import json

        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine_with_failing_synthesizer()
        result = engine.run(ResearchRequest(question="test synthesis failure"))
        json.dumps(serialize(result))  # must not raise


@pytest.mark.engine
class TestClaimExtractionFailure:
    def test_claim_extraction_failure_returns_partial(self) -> None:
        from research_core.contracts.request import ResearchRequest

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            claim_extractor=FailingClaimExtractor(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test"))
        assert result.status == ResearchStatus.PARTIAL

    def test_claim_extraction_failure_preserves_evidence(self) -> None:
        from research_core.contracts.request import ResearchRequest

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            claim_extractor=FailingClaimExtractor(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test"))
        assert len(result.evidence) > 0

    def test_claim_extraction_failure_claims_empty(self) -> None:
        from research_core.contracts.request import ResearchRequest

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            claim_extractor=FailingClaimExtractor(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test"))
        assert result.claims == ()


@pytest.mark.engine
class TestGapAnalysisFailure:
    def test_gap_analysis_failure_returns_partial(self) -> None:
        from research_core.contracts.request import ResearchRequest

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            claim_extractor=SimpleCLaimExtractor(),
            gap_analyzer=FailingGapAnalyzer(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test"))
        assert result.status == ResearchStatus.PARTIAL

    def test_gap_analysis_failure_preserves_claims(self) -> None:
        from research_core.contracts.request import ResearchRequest

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            claim_extractor=SimpleCLaimExtractor(),
            gap_analyzer=FailingGapAnalyzer(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test"))
        assert len(result.claims) > 0


@pytest.mark.engine
class TestKnowledgeFailureWebSucceeds:
    def test_knowledge_fails_web_succeeds_returns_partial(self) -> None:
        from research_core.contracts.request import ResearchRequest

        src = make_source("src-web-1")
        ev = make_evidence("ev-web-1", "src-web-1", source_type="web")  # type: ignore[arg-type]
        engine = ResearchEngine(
            knowledge_provider=FailingKnowledgeProvider(),
            web_search_provider=FixedWebProvider((src,), (ev,)),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test", use_web=True))
        assert result.status == ResearchStatus.PARTIAL
        assert len(result.evidence) > 0

    def test_web_fails_knowledge_succeeds_returns_partial(self) -> None:
        from research_core.contracts.request import ResearchRequest

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            web_search_provider=FailingWebProvider(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test", use_web=True))
        assert result.status == ResearchStatus.PARTIAL
        assert len(result.evidence) > 0


@pytest.mark.engine
class TestStrictMode:
    def test_strict_mode_raises_on_partial(self) -> None:
        from research_core.contracts.request import ResearchRequest
        from research_core.exceptions import IncompleteResearchError

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            synthesizer=FailingSynthesizer(),
            clock=fixed_clock,
        )
        with pytest.raises(IncompleteResearchError):
            engine.run(ResearchRequest(question="test", strict=True))

    def test_strict_mode_does_not_raise_when_complete(self) -> None:
        from research_core.contracts.request import ResearchRequest

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test", strict=True))
        assert result.status == ResearchStatus.COMPLETE
