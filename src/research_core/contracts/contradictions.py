"""
Contradiction contracts.

A Contradiction is an explicit, structured record of a detected conflict between
claims, evidence items, or a combination. Contradictions are first-class outputs
— they must not be absorbed into prose or silently discarded.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from enum import StrEnum

from research_core.contracts.common import (
    EMPTY_METADATA,
    ClaimId,
    ContradictionId,
    EvidenceId,
    Metadata,
    _to_proxy,
)
from research_core.exceptions import ContractValidationError


class ContradictionType(StrEnum):
    """The nature of the conflict.

    NUMERIC        — conflicting numerical estimates (market size, counts, etc.)
    TEMPORAL       — conflicting dates or time periods
    DEFINITIONAL   — conflicting definitions of a term or concept
    SCOPE          — one source covers a broader or different scope than another
    METHODOLOGICAL — conflicting research or measurement methods
    ENTITY_IDENTITY — disagreement about whether two named entities are the same
    CATEGORICAL    — conflicting categorical assertions (growth vs. decline, etc.)
    OTHER          — conflict that does not fit the above categories
    """

    NUMERIC = "numeric"
    TEMPORAL = "temporal"
    DEFINITIONAL = "definitional"
    SCOPE = "scope"
    METHODOLOGICAL = "methodological"
    ENTITY_IDENTITY = "entity_identity"
    CATEGORICAL = "categorical"
    OTHER = "other"


class ContradictionSeverity(StrEnum):
    """How significantly the contradiction undermines the result.

    LOW      — minor or peripheral conflict; does not affect core claims.
    MEDIUM   — notable conflict; affects confidence in specific claims.
    HIGH     — significant conflict; undermines synthesis reliability.
    CRITICAL — fundamental conflict; synthesis is unreliable until resolved.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContradictionResolutionStatus(StrEnum):
    """Whether and how the contradiction has been addressed.

    UNRESOLVED   — conflict is open; no resolution has been applied.
    ACKNOWLEDGED — conflict is noted but not resolved; caller is aware.
    RESOLVED     — conflict has been resolved; resolution_notes explain how.
    """

    UNRESOLVED = "unresolved"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class Contradiction:
    """A structured record of a detected conflict.

    At least two references (claims and/or evidence items, in any combination)
    are required. A conflict between a single claim and a single evidence item
    counts as two references.

    resolution_notes: meaningful only when resolution_status is RESOLVED.
    The contract does not enforce this distinction at the value level, but
    callers must not populate resolution_notes in a way that implies resolution
    when resolution_status is UNRESOLVED or ACKNOWLEDGED.
    """

    contradiction_id: ContradictionId
    contradiction_type: ContradictionType
    description: str
    claim_ids: tuple[ClaimId, ...] = field(default_factory=tuple)
    evidence_ids: tuple[EvidenceId, ...] = field(default_factory=tuple)
    severity: ContradictionSeverity = ContradictionSeverity.MEDIUM
    resolution_status: ContradictionResolutionStatus = (
        ContradictionResolutionStatus.UNRESOLVED
    )
    resolution_notes: str = ""
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.contradiction_id.strip():
            raise ContractValidationError("contradiction_id must not be empty")
        if not self.description.strip():
            raise ContractValidationError("description must not be empty")
        total_refs = len(self.claim_ids) + len(self.evidence_ids)
        if total_refs < 2:
            raise ContractValidationError(
                "a contradiction must reference at least two items "
                f"(claims + evidence combined), got {total_refs}"
            )
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))
