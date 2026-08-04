"""
Execution trace contracts.

A ResearchTrace records the pipeline execution history. Traces are
diagnostic artifacts — they are not required for result correctness.
Consumers should not branch on trace content for business logic.

All timestamps in TraceEvent must be timezone-aware.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from research_core.contracts.common import (
    EMPTY_METADATA,
    Metadata,
    TraceEventId,
    _to_proxy,
)
from research_core.exceptions import ContractValidationError


class TraceStage(StrEnum):
    """Named pipeline stages recorded in the trace.

    Stages appear roughly in execution order; multiple events may share
    a stage (e.g. RETRIEVAL events for each retrieval attempt).
    """

    INIT = "init"
    PROFILE_RESOLUTION = "profile_resolution"
    RETRIEVAL = "retrieval"
    EXTRACTION = "extraction"
    CLAIM_ANALYSIS = "claim_analysis"
    CONTRADICTION_DETECTION = "contradiction_detection"
    GAP_ANALYSIS = "gap_analysis"
    SYNTHESIS = "synthesis"
    RENDERING = "rendering"
    FINALIZATION = "finalization"
    OTHER = "other"


class TraceEventStatus(StrEnum):
    """Outcome of a single trace event."""

    STARTED = "started"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass(frozen=True)
class TraceEvent:
    """A single pipeline event recorded during execution.

    occurred_at: must be timezone-aware.
    duration_ms: wall-clock milliseconds for this event; None if not measured.
    payload: arbitrary structured data for the event (e.g. retrieval query,
             source count, error details). Must be serializable to JSON by
             the caller.
    """

    event_id: TraceEventId
    stage: TraceStage
    status: TraceEventStatus
    message: str
    occurred_at: datetime
    duration_ms: float | None = None
    payload: dict[str, Any] | None = None
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ContractValidationError("event_id must not be empty")
        if not self.message.strip():
            raise ContractValidationError("TraceEvent.message must not be empty")
        if self.occurred_at.tzinfo is None:
            raise ContractValidationError(
                "TraceEvent.occurred_at must be timezone-aware"
            )
        if self.duration_ms is not None and self.duration_ms < 0.0:
            raise ContractValidationError(
                f"duration_ms must be >= 0, got {self.duration_ms}"
            )
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class ResearchTrace:
    """Ordered execution trace for a research pipeline run.

    events: ordered list of trace events; empty is valid (tracing disabled).
    request_id: optional correlation ID supplied by the caller.
    pipeline_version: optional string identifying the engine or version.
    """

    events: tuple[TraceEvent, ...] = field(default_factory=tuple)
    request_id: str | None = None
    pipeline_version: str | None = None
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))

    def events_for_stage(self, stage: TraceStage) -> tuple[TraceEvent, ...]:
        """Return all events for a given stage, in order."""
        return tuple(e for e in self.events if e.stage == stage)

    def failed_events(self) -> tuple[TraceEvent, ...]:
        """Return all events with FAILED status."""
        return tuple(e for e in self.events if e.status == TraceEventStatus.FAILED)
