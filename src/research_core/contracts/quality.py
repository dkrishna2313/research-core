"""
Quality diagnostics contracts.

Quality is multidimensional. A single unexplained scalar must never be the
only signal. Component dimensions are independently accessible. A composite
score is optional and additive — it must not replace component scores.

All scores are normalized to [0.0, 1.0] when present. None means the
dimension was not assessed; it must not be treated as zero.

Contradiction severity and uncertainty are directional:
- contradiction_severity: higher = more severe contradictions (worse quality)
- uncertainty: higher = more uncertainty in claims (worse quality)
All dimensions use the same direction: higher = better, EXCEPT contradiction_severity
and uncertainty where higher indicates a worse quality signal. This is documented
in each QualityDimension's notes field when applicable.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field

from research_core.contracts.common import EMPTY_METADATA, Metadata, _to_proxy
from research_core.exceptions import ContractValidationError


@dataclass(frozen=True)
class QualityDimension:
    """A single quality dimension score.

    score: [0.0, 1.0] or None if not assessed.
    notes: human-readable explanation or context for the score.
    flags: optional string flags (e.g. "low_sample_size", "single_source").

    A None score is meaningfully different from 0.0. None means the dimension
    was not measured. 0.0 means it was measured and scored at the minimum.
    """

    score: float | None = None
    notes: str = ""
    flags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ContractValidationError(
                f"QualityDimension.score must be in [0.0, 1.0], got {self.score}"
            )

    @property
    def is_available(self) -> bool:
        """True if this dimension has been assessed (score is not None)."""
        return self.score is not None


def _default_dim() -> QualityDimension:
    """Factory for an unavailable quality dimension."""
    return QualityDimension(score=None)


@dataclass(frozen=True)
class QualityDiagnostics:
    """Multidimensional quality assessment for a ResearchResult.

    Each dimension is independently accessible. A composite score may be
    provided for convenience but must not replace component scores.

    Directional note for consumers:
    - For relevance, authority, recency, corroboration, independence, coverage,
      completeness, provenance_completeness, reproducibility:
      higher score = better quality.
    - For contradiction_severity and uncertainty:
      higher score = more severe contradictions / more uncertainty (worse signal).
      Consumers should invert or weight these dimensions accordingly.
    """

    relevance: QualityDimension = field(default_factory=_default_dim)
    authority: QualityDimension = field(default_factory=_default_dim)
    recency: QualityDimension = field(default_factory=_default_dim)
    corroboration: QualityDimension = field(default_factory=_default_dim)
    independence: QualityDimension = field(default_factory=_default_dim)
    coverage: QualityDimension = field(default_factory=_default_dim)
    extraction_confidence: QualityDimension = field(default_factory=_default_dim)
    contradiction_severity: QualityDimension = field(default_factory=_default_dim)
    uncertainty: QualityDimension = field(default_factory=_default_dim)
    completeness: QualityDimension = field(default_factory=_default_dim)
    provenance_completeness: QualityDimension = field(default_factory=_default_dim)
    reproducibility: QualityDimension = field(default_factory=_default_dim)
    composite: float | None = None
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if self.composite is not None and not 0.0 <= self.composite <= 1.0:
            raise ContractValidationError(
                f"QualityDiagnostics.composite must be in [0.0, 1.0], got {self.composite}"
            )
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))

    def dimensions(self) -> dict[str, QualityDimension]:
        """Return all named dimensions as a plain dict for inspection."""
        return {
            "relevance": self.relevance,
            "authority": self.authority,
            "recency": self.recency,
            "corroboration": self.corroboration,
            "independence": self.independence,
            "coverage": self.coverage,
            "extraction_confidence": self.extraction_confidence,
            "contradiction_severity": self.contradiction_severity,
            "uncertainty": self.uncertainty,
            "completeness": self.completeness,
            "provenance_completeness": self.provenance_completeness,
            "reproducibility": self.reproducibility,
        }

    def available_dimensions(self) -> dict[str, QualityDimension]:
        """Return only dimensions that have been assessed (score is not None)."""
        return {k: v for k, v in self.dimensions().items() if v.is_available}
