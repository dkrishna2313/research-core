"""
Integration tests for ResearchEngine.run() — real deterministic pipeline.

Uses in-memory providers (no network, no knowledge-layer runtime).
"""

from __future__ import annotations

import pytest

from research_core.contracts.result import ResearchResult, ResearchStatus
from research_core.contracts.serialization import serialize
from research_core.engine import ResearchEngine
from research_core.synthesis.deterministic import DeterministicSynthesizer
from tests.engine.conftest import (
    FixedKnowledgeProvider,
    SimpleCLaimExtractor,
    SimpleGapAnalyzer,
    fixed_clock,
    make_evidence,
    make_source,
)


@pytest.mark.engine
class TestEngineIntegration:
    def _make_engine(self, **kwargs: object) -> ResearchEngine:
        src = make_source("src-1")
        ev = make_evidence("ev-1", "src-1")
        defaults = {
            "knowledge_provider": FixedKnowledgeProvider((src,), (ev,)),
            "claim_extractor": SimpleCLaimExtractor(),
            "gap_analyzer": SimpleGapAnalyzer(),
            "synthesizer": DeterministicSynthesizer(),
            "clock": fixed_clock,
        }
        defaults.update(kwargs)
        return ResearchEngine(**defaults)  # type: ignore[arg-type]

    def test_run_returns_research_result(self, simple_request: object) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine()
        result = engine.run(ResearchRequest(question="test question"))
        assert isinstance(result, ResearchResult)

    def test_result_has_non_empty_sources(self, simple_request: object) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine()
        result = engine.run(ResearchRequest(question="test question"))
        assert len(result.sources) > 0

    def test_result_has_non_empty_evidence(self, simple_request: object) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine()
        result = engine.run(ResearchRequest(question="test question"))
        assert len(result.evidence) > 0

    def test_result_has_non_empty_claims(self, simple_request: object) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine()
        result = engine.run(ResearchRequest(question="test question"))
        assert len(result.claims) > 0

    def test_result_has_quality_diagnostics(self, simple_request: object) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine()
        result = engine.run(ResearchRequest(question="test question"))
        assert result.quality is not None

    def test_result_has_trace(self, simple_request: object) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine()
        result = engine.run(ResearchRequest(question="test question"))
        assert result.trace is not None
        assert len(result.trace.events) > 0

    def test_result_has_synthesis(self, simple_request: object) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine()
        result = engine.run(ResearchRequest(question="test question"))
        assert result.synthesis is not None
        assert result.synthesis.narrative.strip() != ""

    def test_all_evidence_references_resolve(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine()
        result = engine.run(ResearchRequest(question="test question"))
        source_ids = {s.source_id for s in result.sources}
        for ev in result.evidence:
            assert ev.source_id in source_ids

    def test_all_claim_evidence_refs_resolve(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine()
        result = engine.run(ResearchRequest(question="test question"))
        evidence_ids = {ev.evidence_id for ev in result.evidence}
        for cl in result.claims:
            for eid in cl.supporting_evidence_ids:
                assert eid in evidence_ids

    def test_result_is_serializable(self) -> None:
        import json

        from research_core.contracts.request import ResearchRequest

        engine = self._make_engine()
        result = engine.run(ResearchRequest(question="test question"))
        serialized = serialize(result)
        json.dumps(serialized)  # must not raise

    def test_repeated_run_deterministic(self) -> None:

        from research_core.contracts.request import ResearchRequest

        request = ResearchRequest(question="test determinism")
        engine = self._make_engine()
        r1 = engine.run(request)
        r2 = engine.run(request)

        # Status, counts, synthesis narrative must match
        assert r1.status == r2.status
        assert len(r1.sources) == len(r2.sources)
        assert len(r1.evidence) == len(r2.evidence)
        assert len(r1.claims) == len(r2.claims)
        assert len(r1.gaps) == len(r2.gaps)
        if r1.synthesis and r2.synthesis:
            assert r1.synthesis.narrative == r2.synthesis.narrative
            assert r1.synthesis.key_findings == r2.synthesis.key_findings


@pytest.mark.engine
class TestEngineWebSkipped:
    def test_web_skipped_when_use_web_false(self) -> None:
        from research_core.contracts.request import ResearchRequest
        from research_core.contracts.trace import TraceEventStatus, TraceStage

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            web_search_provider=None,
            clock=fixed_clock,
        )
        request = ResearchRequest(question="test", use_web=False)
        result = engine.run(request)
        assert result.trace is not None
        web_skips = [
            e for e in result.trace.events
            if e.stage == TraceStage.RETRIEVAL and e.status == TraceEventStatus.SKIPPED
            and "web" in e.message.lower()
        ]
        assert len(web_skips) > 0


@pytest.mark.engine
class TestEngineStatusComplete:
    def test_complete_when_no_failures(self) -> None:
        from research_core.contracts.request import ResearchRequest

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test"))
        assert result.status == ResearchStatus.COMPLETE
        assert result.is_complete
