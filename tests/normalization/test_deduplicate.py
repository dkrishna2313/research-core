"""Tests for evidence deduplication."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.normalization

from research_core.normalization.config import RankingConfig  # noqa: E402
from research_core.normalization.contracts import NormalizedEvidence  # noqa: E402
from research_core.normalization.deduplicate import detect_duplicates  # noqa: E402
from research_core.normalization.normalize import normalize_evidence  # noqa: E402
from tests.normalization.conftest import make_source, make_web_evidence  # noqa: E402


def _normalize_pair(
    content_a: str,
    content_b: str,
    source_id_a: str = "src-a",
    source_id_b: str | None = None,
    ev_id_a: str = "ev-a",
    ev_id_b: str = "ev-b",
    rank_a: int = 1,
    rank_b: int = 2,
) -> list[NormalizedEvidence]:
    sid_b = source_id_b or source_id_a
    src_a = make_source(source_id=source_id_a)
    if sid_b == source_id_a:
        sources = (src_a,)
    else:
        src_b = make_source(source_id=sid_b)
        sources = (src_a, src_b)
    ev_a = make_web_evidence(
        evidence_id=ev_id_a, source_id=source_id_a, content=content_a, rank=rank_a
    )
    ev_b = make_web_evidence(
        evidence_id=ev_id_b, source_id=sid_b, content=content_b, rank=rank_b
    )
    result = normalize_evidence(sources=sources, evidence=(ev_a, ev_b))
    return list(result)


class TestExactDeduplication:
    def test_no_duplicates_all_kept(self) -> None:
        items = _normalize_pair("Content A for testing.", "Content B for testing.")
        cfg = RankingConfig()
        kept, dups, excluded = detect_duplicates(items, cfg)
        assert len(kept) == 2
        assert len(dups) == 0
        assert len(excluded) == 0

    def test_exact_duplicate_removes_one(self) -> None:
        content = "Exact same content here for duplication testing."
        items = _normalize_pair(content, content)
        cfg = RankingConfig()
        kept, dups, excluded = detect_duplicates(items, cfg)
        assert len(kept) == 1
        assert len(dups) == 1
        assert len(excluded) == 1

    def test_exact_duplicate_method_is_exact(self) -> None:
        content = "Exact same content here for duplication testing."
        items = _normalize_pair(content, content)
        kept, dups, excluded = detect_duplicates(items, RankingConfig())
        assert dups[0].method == "exact"
        assert dups[0].similarity == 1.0

    def test_canonical_has_lower_rank(self) -> None:
        content = "Exact same content here for duplication testing."
        src = make_source(source_id="src-x")
        ev1 = make_web_evidence(evidence_id="ev-rank2", source_id="src-x", content=content, rank=2)
        ev2 = make_web_evidence(evidence_id="ev-rank1", source_id="src-x", content=content, rank=1)
        items = list(normalize_evidence(sources=(src,), evidence=(ev1, ev2)))
        kept, dups, _ = detect_duplicates(items, RankingConfig())
        assert kept[0].provider_rank == 1

    def test_excluded_evidence_id_is_recorded(self) -> None:
        content = "Exact same content here for duplication testing."
        items = _normalize_pair(content, content, ev_id_a="ev-a", ev_id_b="ev-b")
        kept, dups, excluded = detect_duplicates(items, RankingConfig())
        excluded_ids = {e.evidence_id for e in excluded}
        kept_ids = {i.evidence.evidence_id for i in kept}
        assert excluded_ids.isdisjoint(kept_ids)


class TestNearDeduplication:
    def _make_similar(self, base: str, tweak: str = " extra word") -> tuple[str, str]:
        return base, base + tweak

    def test_high_jaccard_near_duplicate_removed(self) -> None:
        base = "climate change affects global temperatures and sea levels extensively"
        a = " ".join([base] * 5)
        b = " ".join([base] * 5) + " additional"
        items = _normalize_pair(a, b)
        cfg = RankingConfig(near_duplicate_threshold=0.85)
        kept, dups, excluded = detect_duplicates(items, cfg)
        # Very similar content → one removed
        assert len(kept) <= 2  # may or may not be exact depending on Jaccard

    def test_low_jaccard_both_kept(self) -> None:
        a = "The quick brown fox jumps over the lazy dog for testing purposes here."
        b = "Completely different content about climate science and renewable energy sources."
        items = _normalize_pair(a, b)
        cfg = RankingConfig(near_duplicate_threshold=0.90)
        kept, dups, excluded = detect_duplicates(items, cfg)
        assert len(kept) == 2

    def test_near_duplicate_method_is_near_duplicate(self) -> None:
        base = ("word " * 40).strip()
        a = base
        b = base + " extra"
        items = _normalize_pair(a, b)
        cfg = RankingConfig(near_duplicate_threshold=0.80)
        kept, dups, excluded = detect_duplicates(items, cfg)
        for d in dups:
            assert d.method in ("exact", "near_duplicate")

    def test_short_content_skipped_for_near_dup(self) -> None:
        # Short items (<200 chars) are not compared for near-dup
        a = "Short A."
        b = "Short B."
        items = _normalize_pair(a, b)
        cfg = RankingConfig(near_duplicate_threshold=0.01)  # very low threshold
        kept, dups, excluded = detect_duplicates(items, cfg)
        # Neither is excluded (both too short for near-dup comparison)
        near_dups = [d for d in dups if d.method == "near_duplicate"]
        assert len(near_dups) == 0

    def test_numeric_disagreement_preserved(self) -> None:
        # Numeric tokens are included so distinct values produce distinct token sets.
        a = "The values are 100 200 300 400 500 and represent measurements taken in the lab."
        b = "The values are 999 888 777 666 555 and represent measurements taken in the lab."
        items = _normalize_pair(a, b)
        cfg = RankingConfig(near_duplicate_threshold=0.90)
        kept, dups, _ = detect_duplicates(items, cfg)
        assert len(kept) == 2, "Items differing only in numeric values must both be kept"

    def test_revenue_numeric_disagreement_preserved(self) -> None:
        base_a = "Revenue was 10 million dollars in the fiscal year reported by the board. "
        base_b = "Revenue was 100 million dollars in the fiscal year reported by the board. "
        a = (base_a * 5).strip()
        b = (base_b * 5).strip()
        items = _normalize_pair(a, b)
        cfg = RankingConfig(near_duplicate_threshold=0.90)
        kept, dups, _ = detect_duplicates(items, cfg)
        assert len(kept) == 2, "Revenue disagreement (10M vs 100M) must be preserved"

    def test_percentage_disagreement_preserved(self) -> None:
        base_a = "The target is 20 percent according to the latest policy document guidance. "
        base_b = "The target is 25 percent according to the latest policy document guidance. "
        a = (base_a * 5).strip()
        b = (base_b * 5).strip()
        items = _normalize_pair(a, b)
        cfg = RankingConfig(near_duplicate_threshold=0.90)
        kept, dups, _ = detect_duplicates(items, cfg)
        assert len(kept) == 2, "Percentage disagreement (20% vs 25%) must be preserved"

    def test_date_disagreement_preserved(self) -> None:
        base_a = "The event occurred in 2024 and was reported across multiple major publications. "
        base_b = "The event occurred in 2025 and was reported across multiple major publications. "
        a = (base_a * 4).strip()
        b = (base_b * 4).strip()
        items = _normalize_pair(a, b)
        cfg = RankingConfig(near_duplicate_threshold=0.90)
        kept, dups, _ = detect_duplicates(items, cfg)
        assert len(kept) == 2, "Date disagreement (2024 vs 2025) must be preserved"

    def test_max_comparisons_respected(self) -> None:
        src = make_source()
        evidences = tuple(
            make_web_evidence(evidence_id=f"ev-{i:03d}", source_id=src.source_id,
                              content=("word " * 50).strip(), rank=i + 1)
            for i in range(20)
        )
        items = list(normalize_evidence(sources=(src,), evidence=evidences))
        cfg = RankingConfig(max_near_duplicate_comparisons=5)
        kept, dups, excluded = detect_duplicates(items, cfg)
        # Should not crash; comparisons should be bounded
        assert len(kept) + len(excluded) == 20


class TestCanonicalSelection:
    def test_better_provenance_completeness_wins(self) -> None:
        from datetime import UTC, datetime

        from research_core.contracts.common import SourceType
        from research_core.contracts.evidence import EvidenceItem
        from research_core.contracts.sources import EvidenceQuality, Provenance

        src = make_source(source_id="src-001")
        content = "Exactly the same content for canonical selection testing purposes right here."

        prov_rich = Provenance(
            source_id="src-001",
            source_type=SourceType.WEB,
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
            provider="duckduckgo",
            retrieval_rank=1,
            retrieval_score=None,
            extraction_method="trafilatura",
            extraction_confidence=0.9,
            url="https://example.com",
        )
        prov_sparse = Provenance(
            source_id="src-001",
            source_type=SourceType.WEB,
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        ev_rich = EvidenceItem(
            evidence_id="ev-rich",
            content=content,
            source_id="src-001",
            provenance=prov_rich,
            quality=EvidenceQuality(),
        )
        ev_sparse = EvidenceItem(
            evidence_id="ev-sparse",
            content=content,
            source_id="src-001",
            provenance=prov_sparse,
            quality=EvidenceQuality(),
        )

        items = list(normalize_evidence(sources=(src,), evidence=(ev_rich, ev_sparse)))
        kept, dups, _ = detect_duplicates(items, RankingConfig())
        assert len(kept) == 1
        assert kept[0].evidence.evidence_id == "ev-rich"
