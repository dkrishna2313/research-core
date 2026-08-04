"""
Contracts for the evidence normalization and ranking layer.

These types represent normalized, deduplicated, and ranked evidence items
along with capability reporting for knowledge and web adapters.

None means "not assessed / not available" throughout — never 0.0.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from enum import StrEnum

from research_core.contracts.common import EMPTY_METADATA, Metadata, _to_proxy
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.sources import Source


class CapabilityStatus(StrEnum):
    """Status of a single adapter capability."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AdapterCapability:
    """Status of one capability offered by an adapter."""

    name: str
    status: CapabilityStatus
    description: str = ""
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class CapabilityReport:
    """Aggregated capability report for an adapter instance."""

    adapter_name: str
    capabilities: tuple[AdapterCapability, ...]
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


class ComponentStatus(StrEnum):
    """Status of a single ranking component for one evidence item."""

    AVAILABLE = "available"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"
    PENALTY = "penalty"
    BONUS = "bonus"


@dataclass(frozen=True)
class RankingComponent:
    """Score and weight for one ranking dimension, for full explainability."""

    name: str
    status: ComponentStatus
    raw_value: float | None
    normalized_value: float | None
    weight_used: float
    notes: str = ""


@dataclass(frozen=True)
class NormalizedEvidence:
    """Evidence item with normalized retrieval signals and segmentation metadata.

    provider_score is the raw score from the provider (None for web).
    normalized_retrieval_signal is a [0,1] signal usable for ranking:
      - Knowledge: same as provider_score (already [0,1])
      - Web (rank known): 1.0 / (1.0 + log2(rank + 1))  — rank-position feature
      - Web (no rank, no score): None

    segment_index / segment_count / parent_evidence_id are set only when the
    evidence item is a segment produced by the segmenter; otherwise None.
    """

    evidence: EvidenceItem
    source: Source
    provider: str
    provider_rank: int | None
    provider_score: float | None
    normalized_retrieval_signal: float | None
    content_length: int
    segment_index: int | None = None
    segment_count: int | None = None
    parent_evidence_id: str | None = None
    duplicate_of: str | None = None
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class RankedEvidence:
    """Evidence item with a final rank and a fully explainable composite score.

    score is a deterministic [0,1] ranking signal — NOT a probability or truth score.
    rank is 1-based.
    components records per-dimension scores for full explainability.
    """

    normalized_evidence: NormalizedEvidence
    rank: int
    score: float
    components: tuple[RankingComponent, ...]
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class DuplicateEvidence:
    """Record of an evidence item that was found to be a duplicate."""

    evidence_id: str
    canonical_id: str
    similarity: float
    method: str  # "exact" or "near_duplicate"


@dataclass(frozen=True)
class ExcludedEvidence:
    """Record of an evidence item excluded from ranking."""

    evidence_id: str
    reason: str


@dataclass(frozen=True)
class RankingDiagnostics:
    """Aggregate diagnostics from a ranking run."""

    total_input: int
    total_ranked: int
    total_excluded: int
    total_duplicates: int
    config_fingerprint: str
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class EvidenceRankingResult:
    """Complete output of a ranking pipeline run."""

    ranked: tuple[RankedEvidence, ...]
    excluded: tuple[ExcludedEvidence, ...]
    duplicates: tuple[DuplicateEvidence, ...]
    diagnostics: RankingDiagnostics
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))
