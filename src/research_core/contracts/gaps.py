"""
ResearchGap and OpenQuestion contracts.

Research gaps are first-class, evidence-aware outputs. The system must never
report an empty gap list when evidence is absent, weak, or incomplete.

Open questions are research questions that remain unresolved after synthesis.
They are distinct from product-owner implementation questions.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from enum import StrEnum

from research_core.contracts.common import (
    EMPTY_METADATA,
    ClaimId,
    EvidenceId,
    Metadata,
    ResearchGapId,
    _to_proxy,
)
from research_core.exceptions import ContractValidationError


class GapType(StrEnum):
    """The evidence-aware reason for a gap.

    All types are domain-neutral. Domain-specific gap types belong in
    consumer-supplied analytical lenses, not in the core schema.
    """

    NO_EVIDENCE = "no_evidence"
    INSUFFICIENT_COVERAGE = "insufficient_coverage"
    WEAK_AUTHORITY = "weak_authority"
    UNCORROBORATED_CLAIM = "uncorroborated_claim"
    STALE_EVIDENCE = "stale_evidence"
    UNRESOLVED_CONTRADICTION = "unresolved_contradiction"
    LOW_EXTRACTION_CONFIDENCE = "low_extraction_confidence"
    MISSING_DIMENSION = "missing_dimension"
    METHODOLOGICAL_UNCERTAINTY = "methodological_uncertainty"
    INCONSISTENT_DEFINITION = "inconsistent_definition"
    OTHER = "other"


class GapSeverity(StrEnum):
    """How significantly the gap affects the result reliability."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GapStatus(StrEnum):
    """Whether the gap has been acted upon."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    ADDRESSED = "addressed"


@dataclass(frozen=True)
class ResearchGap:
    """An identified gap in evidence coverage.

    condition: stable internal condition identifier that produced this gap
    (e.g. "no_sources", "no_evidence"). Empty string when not set by the emitter.

    recommended_action: a research action (e.g. "retrieve additional sources",
    "verify with primary data") — not a business-strategy recommendation.
    """

    gap_id: ResearchGapId
    gap_type: GapType
    description: str
    related_claim_ids: tuple[ClaimId, ...] = field(default_factory=tuple)
    related_evidence_ids: tuple[EvidenceId, ...] = field(default_factory=tuple)
    severity: GapSeverity = GapSeverity.MEDIUM
    recommended_action: str = ""
    status: GapStatus = GapStatus.OPEN
    condition: str = ""
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.gap_id.strip():
            raise ContractValidationError("gap_id must not be empty")
        if not self.description.strip():
            raise ContractValidationError("description must not be empty")
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


class QuestionPriority(StrEnum):
    """Relative importance of an open research question."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class OpenQuestion:
    """A research question that remains unresolved after synthesis.

    Open questions are research questions — they emerge from gaps in the
    evidence and are candidates for follow-up research. They are not
    product-owner implementation questions.
    """

    question: str
    reason: str = ""
    priority: QuestionPriority = QuestionPriority.MEDIUM
    related_claim_ids: tuple[ClaimId, ...] = field(default_factory=tuple)
    related_gap_ids: tuple[ResearchGapId, ...] = field(default_factory=tuple)
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ContractValidationError("open question text must not be empty")
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))
