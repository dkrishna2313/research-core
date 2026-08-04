"""
EvidenceItem and related types.

An EvidenceItem is a discrete piece of retrieved content. It is distinct from a
Claim: evidence is a retrievable artifact; a claim is an assertion derived from
evidence. One evidence item may support, weaken, or contradict different claims
— so the relationship between evidence and claims is expressed through
EvidenceClaimLink objects rather than a single relationship field.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from research_core.contracts.common import (
    EMPTY_METADATA,
    ClaimId,
    EvidenceId,
    Metadata,
    SourceId,
    _to_proxy,
)
from research_core.contracts.sources import EvidenceQuality, Provenance
from research_core.exceptions import ContractValidationError


class EvidenceRelationship(StrEnum):
    """The directional relationship between an evidence item and a claim.

    SUPPORTS    — the evidence strengthens the claim.
    WEAKENS     — the evidence reduces confidence in the claim without
                  directly contradicting it.
    CONTRADICTS — the evidence directly conflicts with the claim.
    NEUTRAL     — the evidence is topically related but neither strengthens
                  nor weakens the claim.
    """

    SUPPORTS = "supports"
    WEAKENS = "weakens"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class EvidenceClaimLink:
    """Typed association between an evidence item and a specific claim.

    Using per-claim links instead of a single global relationship field allows
    one evidence item to simultaneously support one claim and weaken another —
    a common situation when evidence contains nuanced information.

    confidence: [0.0, 1.0] — how confident the link assignment is.
    notes: optional human-readable rationale for the assignment.
    """

    claim_id: ClaimId
    relationship: EvidenceRelationship
    confidence: float = 1.0
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise ContractValidationError("claim_id in EvidenceClaimLink must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ContractValidationError(
                f"EvidenceClaimLink.confidence must be in [0.0, 1.0], got {self.confidence}"
            )


@dataclass(frozen=True)
class EvidenceItem:
    """A discrete piece of retrieved content with full provenance.

    content: the extracted text excerpt (never the full raw page).
    source_id: references a Source in the result's sources collection.
    provenance: full retrieval and extraction lineage.
    quality: item-level quality signals (distinct from result-level diagnostics).
    claim_links: typed associations to claims (may be empty before claim extraction).
    locator: optional source-relative location (e.g. "page 3", "section 2.1").
    observed_at: when this evidence item was recorded in the pipeline; must be
                 timezone-aware if provided.
    """

    evidence_id: EvidenceId
    content: str
    source_id: SourceId
    provenance: Provenance
    quality: EvidenceQuality
    claim_links: tuple[EvidenceClaimLink, ...] = field(default_factory=tuple)
    locator: str | None = None
    observed_at: datetime | None = None
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ContractValidationError("evidence_id must not be empty")
        if not self.content.strip():
            raise ContractValidationError("content must not be empty")
        if not self.source_id.strip():
            raise ContractValidationError("source_id must not be empty")
        if self.observed_at is not None and self.observed_at.tzinfo is None:
            raise ContractValidationError("observed_at must be timezone-aware if provided")
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))
