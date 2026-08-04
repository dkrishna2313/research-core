"""
EvidenceNormalizer — convenience wrapper around normalize_evidence().
"""

from __future__ import annotations

from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.sources import Source
from research_core.normalization.config import NormalizationConfig
from research_core.normalization.contracts import NormalizedEvidence
from research_core.normalization.normalize import normalize_evidence


class EvidenceNormalizer:
    """Stateless convenience wrapper around normalize_evidence().

    Config is set at construction time and reused for every normalize() call.
    """

    def __init__(self, config: NormalizationConfig | None = None) -> None:
        self._config = config or NormalizationConfig()

    def normalize(
        self,
        *,
        sources: tuple[Source, ...],
        evidence: tuple[EvidenceItem, ...],
    ) -> tuple[NormalizedEvidence, ...]:
        """Normalize and segment evidence items."""
        return normalize_evidence(sources=sources, evidence=evidence, config=self._config)
