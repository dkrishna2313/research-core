"""
Tests for engine execution trace behavior.
"""

from __future__ import annotations

import pytest

from research_core.contracts.trace import TraceEventStatus, TraceStage
from research_core.engine import ResearchEngine
from tests.engine.conftest import (
    FixedKnowledgeProvider,
    SimpleCLaimExtractor,
    SimpleGapAnalyzer,
    fixed_clock,
    make_evidence,
    make_source,
)


@pytest.mark.engine
class TestTrace:
    def _engine_with_all_stages(self) -> ResearchEngine:
        from research_core.synthesis.deterministic import DeterministicSynthesizer

        src = make_source()
        ev = make_evidence()
        return ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            claim_extractor=SimpleCLaimExtractor(),
            gap_analyzer=SimpleGapAnalyzer(),
            synthesizer=DeterministicSynthesizer(),
            clock=fixed_clock,
        )

    def test_trace_is_not_none(self) -> None:
        from research_core.contracts.request import ResearchRequest

        result = self._engine_with_all_stages().run(ResearchRequest(question="test"))
        assert result.trace is not None

    def test_trace_has_events(self) -> None:
        from research_core.contracts.request import ResearchRequest

        result = self._engine_with_all_stages().run(ResearchRequest(question="test"))
        assert result.trace is not None
        assert len(result.trace.events) > 0

    def test_trace_events_have_unique_ids(self) -> None:
        from research_core.contracts.request import ResearchRequest

        result = self._engine_with_all_stages().run(ResearchRequest(question="test"))
        assert result.trace is not None
        ids = [e.event_id for e in result.trace.events]
        assert len(ids) == len(set(ids))

    def test_trace_events_have_non_empty_messages(self) -> None:
        from research_core.contracts.request import ResearchRequest

        result = self._engine_with_all_stages().run(ResearchRequest(question="test"))
        assert result.trace is not None
        for event in result.trace.events:
            assert event.message.strip()

    def test_trace_has_init_event(self) -> None:
        from research_core.contracts.request import ResearchRequest

        result = self._engine_with_all_stages().run(ResearchRequest(question="test"))
        assert result.trace is not None
        init_events = [e for e in result.trace.events if e.stage == TraceStage.INIT]
        assert len(init_events) >= 1

    def test_trace_has_finalization_event(self) -> None:
        from research_core.contracts.request import ResearchRequest

        result = self._engine_with_all_stages().run(ResearchRequest(question="test"))
        assert result.trace is not None
        fin_events = [e for e in result.trace.events if e.stage == TraceStage.FINALIZATION]
        assert len(fin_events) >= 1

    def test_trace_timestamps_are_timezone_aware(self) -> None:
        from research_core.contracts.request import ResearchRequest

        result = self._engine_with_all_stages().run(ResearchRequest(question="test"))
        assert result.trace is not None
        for event in result.trace.events:
            assert event.occurred_at.tzinfo is not None

    def test_trace_serializes(self) -> None:
        import json

        from research_core.contracts.request import ResearchRequest
        from research_core.contracts.serialization import serialize

        result = self._engine_with_all_stages().run(ResearchRequest(question="test"))
        assert result.trace is not None
        json.dumps(serialize(result.trace))

    def test_web_skipped_trace_when_not_requested(self) -> None:
        from research_core.contracts.request import ResearchRequest

        result = self._engine_with_all_stages().run(
            ResearchRequest(question="test", use_web=False)
        )
        assert result.trace is not None
        web_skips = [
            e for e in result.trace.events
            if e.stage == TraceStage.RETRIEVAL
            and e.status == TraceEventStatus.SKIPPED
            and "web" in e.message.lower()
        ]
        assert len(web_skips) > 0

    def test_synthesis_failure_recorded_in_trace(self) -> None:
        from research_core.contracts.request import ResearchRequest
        from tests.engine.conftest import FailingSynthesizer

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            synthesizer=FailingSynthesizer(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test"))
        assert result.trace is not None
        failed = [
            e for e in result.trace.events
            if e.stage == TraceStage.SYNTHESIS and e.status == TraceEventStatus.FAILED
        ]
        assert len(failed) == 1

    def test_no_traceback_in_trace_messages(self) -> None:
        from research_core.contracts.request import ResearchRequest
        from tests.engine.conftest import FailingSynthesizer

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            synthesizer=FailingSynthesizer(),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test"))
        assert result.trace is not None
        for event in result.trace.events:
            assert "Traceback" not in event.message
            assert "File \"" not in event.message
