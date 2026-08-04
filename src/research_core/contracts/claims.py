"""
Claim contracts.

A Claim is a discrete factual or analytical assertion derived from evidence. It
is not the evidence itself. Claims reference the evidence IDs that support or
conflict with them; they never embed evidence content.
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
    _to_proxy,
)
from research_core.exceptions import ContractValidationError


class ClaimType(StrEnum):
    """Domain-neutral category of a claim.

    Kept minimal to avoid domain-specific ontology. Callers may supply
    richer categorization through qualifiers or metadata.
    """

    FACTUAL = "factual"
    ANALYTICAL = "analytical"
    PREDICTIVE = "predictive"
    NORMATIVE = "normative"
    DEFINITIONAL = "definitional"
    OTHER = "other"


class ClaimStatus(StrEnum):
    """Epistemic status of a claim given the available evidence.

    SUPPORTED          — multiple independent sources corroborate the claim.
    PARTIALLY_SUPPORTED — some evidence supports the claim; coverage or
                         corroboration is incomplete.
    CONTESTED          — evidence both supports and contradicts the claim.
    UNSUPPORTED        — no supporting evidence was found.
    UNRESOLVED         — status has not yet been determined (default before
                         claim analysis runs).

    SUPPORTED must not be assigned solely because a web source asserts
    something. Authority, corroboration, and recency must be considered.
    """

    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTESTED = "contested"
    UNSUPPORTED = "unsupported"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class Claim:
    """A discrete assertion extracted from evidence.

    statement: the claim in plain language; must be non-empty.
    qualifiers: optional constraints on scope (dates, geography, methodology,
                definitions, units). Stored as immutable strings; callers
                decide structure. No domain-specific fields are pre-defined.
    supporting_evidence_ids / conflicting_evidence_ids: references to
                EvidenceItem.evidence_id values. Claims never embed evidence
                bodies.
    confidence: [0.0, 1.0] — extraction or assignment confidence; not a
                measure of factual certainty.
    """

    claim_id: ClaimId
    statement: str
    claim_type: ClaimType = ClaimType.FACTUAL
    scope: str = ""
    qualifiers: tuple[str, ...] = field(default_factory=tuple)
    supporting_evidence_ids: tuple[EvidenceId, ...] = field(default_factory=tuple)
    conflicting_evidence_ids: tuple[EvidenceId, ...] = field(default_factory=tuple)
    confidence: float = 0.0
    status: ClaimStatus = ClaimStatus.UNRESOLVED
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise ContractValidationError("claim_id must not be empty")
        if not self.statement.strip():
            raise ContractValidationError("statement must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ContractValidationError(
                f"confidence must be in [0.0, 1.0], got {self.confidence}"
            )
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))
