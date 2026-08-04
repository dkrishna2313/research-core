"""Tests for EvidenceRanker convenience class."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.normalization

from research_core.normalization.config import RankingConfig  # noqa: E402
from research_core.normalization.contracts import (  # noqa: E402
    EvidenceRankingResult,
    NormalizedEvidence,
)
from research_core.normalization.normalize import normalize_evidence  # noqa: E402
from research_core.normalization.ranker import EvidenceRanker  # noqa: E402
from tests.normalization.conftest import make_source, make_web_evidence  # noqa: E402


def _make_normalized(count: int = 2) -> tuple[NormalizedEvidence, ...]:
    src = make_source()
    evidences = tuple(
        make_web_evidence(evidence_id=f"ev-{i:02d}", source_id=src.source_id, rank=i + 1)
        for i in range(count)
    )
    return normalize_evidence(sources=(src,), evidence=evidences)


class TestEvidenceRanker:
    def test_default_config_used(self) -> None:
        ranker = EvidenceRanker()
        assert ranker._config == RankingConfig()

    def test_rank_returns_evidence_ranking_result(self) -> None:
        ranker = EvidenceRanker()
        items = _make_normalized(3)
        result = ranker.rank(items)
        assert isinstance(result, EvidenceRankingResult)

    def test_duplicates_reflected_in_diagnostics(self) -> None:
        src = make_source()
        content = "Identical content used to test deduplication in the ranker pipeline."
        ev1 = make_web_evidence(
            evidence_id="ev-dup-a", source_id=src.source_id, content=content, rank=1
        )
        ev2 = make_web_evidence(
            evidence_id="ev-dup-b", source_id=src.source_id, content=content, rank=2
        )
        items = normalize_evidence(sources=(src,), evidence=(ev1, ev2))
        ranker = EvidenceRanker()
        result = ranker.rank(items)
        assert result.diagnostics.total_duplicates >= 1

    def test_ranked_items_ordered_by_rank(self) -> None:
        ranker = EvidenceRanker()
        items = _make_normalized(4)
        result = ranker.rank(items)
        ranks = [r.rank for r in result.ranked]
        assert ranks == sorted(ranks)

    def test_custom_config_used(self) -> None:
        cfg = RankingConfig(near_duplicate_threshold=0.50)
        ranker = EvidenceRanker(config=cfg)
        items = _make_normalized(2)
        result = ranker.rank(items)
        assert result.diagnostics.config_fingerprint == cfg.fingerprint
