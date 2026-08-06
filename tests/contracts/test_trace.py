"""Tests for TraceEvent and ResearchTrace contracts."""

from __future__ import annotations

import types
from datetime import datetime

import pytest

from research_core.contracts.trace import (
    ResearchTrace,
    TraceEventStatus,
    TraceStage,
)
from research_core.exceptions import ContractValidationError
from tests.conftest import FIXED_TS, make_trace_event


class TestTraceEvent:
    def test_minimal_construction(self) -> None:
        evt = make_trace_event()
        assert evt.event_id == "evt-1"
        assert evt.occurred_at == FIXED_TS

    def test_empty_event_id_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_trace_event(event_id="")

    def test_empty_message_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_trace_event(message="")

    def test_naive_occurred_at_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="timezone"):
            make_trace_event(occurred_at=datetime(2024, 1, 1))

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_trace_event(duration_ms=-1.0)

    def test_zero_duration_accepted(self) -> None:
        evt = make_trace_event(duration_ms=0.0)
        assert evt.duration_ms == 0.0

    def test_metadata_wrapped(self) -> None:
        evt = make_trace_event(metadata={"k": "v"})
        assert isinstance(evt.metadata, types.MappingProxyType)

    def test_is_frozen(self) -> None:
        evt = make_trace_event()
        with pytest.raises((AttributeError, TypeError)):
            evt.message = "changed"  # type: ignore[misc]


class TestTraceStage:
    def test_all_expected_stages_exist(self) -> None:
        expected = {
            "INIT", "PROFILE_RESOLUTION", "RETRIEVAL",
            "NORMALIZATION", "RANKING",
            "EXTRACTION", "CLAIM_ANALYSIS", "CONTRADICTION_DETECTION",
            "GAP_ANALYSIS", "SYNTHESIS", "RENDERING", "FINALIZATION", "OTHER",
        }
        assert {m.name for m in TraceStage} == expected

    def test_values_are_strings(self) -> None:
        for member in TraceStage:
            assert isinstance(member.value, str)


class TestResearchTrace:
    def test_empty_trace_is_valid(self) -> None:
        trace = ResearchTrace()
        assert trace.events == ()

    def test_events_for_stage(self) -> None:
        evt1 = make_trace_event(event_id="e1", stage=TraceStage.RETRIEVAL)
        evt2 = make_trace_event(event_id="e2", stage=TraceStage.SYNTHESIS)
        trace = ResearchTrace(events=(evt1, evt2))
        assert trace.events_for_stage(TraceStage.RETRIEVAL) == (evt1,)
        assert trace.events_for_stage(TraceStage.SYNTHESIS) == (evt2,)

    def test_failed_events(self) -> None:
        evt_ok = make_trace_event(event_id="e1", status=TraceEventStatus.COMPLETED)
        evt_fail = make_trace_event(event_id="e2", status=TraceEventStatus.FAILED)
        trace = ResearchTrace(events=(evt_ok, evt_fail))
        assert trace.failed_events() == (evt_fail,)

    def test_metadata_wrapped(self) -> None:
        trace = ResearchTrace(metadata={"run": "1"})
        assert isinstance(trace.metadata, types.MappingProxyType)
