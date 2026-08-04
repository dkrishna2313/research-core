"""
EvidenceRanker — convenience wrapper that deduplicates then ranks NormalizedEvidence.
"""

from __future__ import annotations

from research_core.normalization.config import RankingConfig
from research_core.normalization.contracts import EvidenceRankingResult, NormalizedEvidence
from research_core.normalization.deduplicate import detect_duplicates
from research_core.normalization.ranking import rank_evidence


class EvidenceRanker:
    """Stateless convenience wrapper: deduplicates then ranks NormalizedEvidence.

    Config is set at construction time and reused for every rank() call.
    """

    def __init__(self, config: RankingConfig | None = None) -> None:
        self._config = config or RankingConfig()

    def rank(self, items: tuple[NormalizedEvidence, ...]) -> EvidenceRankingResult:
        """Deduplicate and rank evidence items, returning a full EvidenceRankingResult."""
        kept, duplicates, excluded = detect_duplicates(list(items), self._config)
        return rank_evidence(kept, duplicates, excluded, self._config)
