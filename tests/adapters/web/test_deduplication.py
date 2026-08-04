"""Tests for URL deduplication in the web adapter."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.web

from research_core.adapters.web.adapter import _dedup_hits  # noqa: E402

from .conftest import make_search_hit  # noqa: E402


class TestDedupHits:
    def test_exact_duplicate_url_removed(self) -> None:
        hits = (
            make_search_hit(rank=1, url="https://example.com/page"),
            make_search_hit(rank=2, url="https://example.com/page"),
        )
        result = _dedup_hits(hits, max_pages=10)
        assert len(result) == 1

    def test_fragment_variants_deduplicated(self) -> None:
        hits = (
            make_search_hit(rank=1, url="https://example.com/page"),
            make_search_hit(rank=2, url="https://example.com/page#section"),
        )
        result = _dedup_hits(hits, max_pages=10)
        assert len(result) == 1

    def test_distinct_urls_preserved(self) -> None:
        hits = (
            make_search_hit(rank=1, url="https://example.com/a"),
            make_search_hit(rank=2, url="https://example.com/b"),
        )
        result = _dedup_hits(hits, max_pages=10)
        assert len(result) == 2

    def test_max_pages_limit_respected(self) -> None:
        hits = tuple(
            make_search_hit(rank=i + 1, url=f"https://example.com/{i}")
            for i in range(10)
        )
        result = _dedup_hits(hits, max_pages=3)
        assert len(result) == 3

    def test_invalid_scheme_dropped(self) -> None:
        hits = (
            make_search_hit(rank=1, url="javascript:void(0)"),
            make_search_hit(rank=2, url="https://example.com/valid"),
        )
        result = _dedup_hits(hits, max_pages=10)
        assert len(result) == 1
        assert result[0].url == "https://example.com/valid"

    def test_file_scheme_dropped(self) -> None:
        hits = (
            make_search_hit(rank=1, url="file:///etc/passwd"),
            make_search_hit(rank=2, url="https://example.com/valid"),
        )
        result = _dedup_hits(hits, max_pages=10)
        assert len(result) == 1

    def test_order_follows_original_rank(self) -> None:
        hits = (
            make_search_hit(rank=1, url="https://example.com/a"),
            make_search_hit(rank=2, url="https://example.com/b"),
            make_search_hit(rank=3, url="https://example.com/c"),
        )
        result = _dedup_hits(hits, max_pages=10)
        assert [h.url for h in result] == [
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/c",
        ]

    def test_first_occurrence_wins_on_duplicate(self) -> None:
        hits = (
            make_search_hit(rank=1, url="https://example.com/page", title="First"),
            make_search_hit(rank=2, url="https://example.com/page", title="Second"),
        )
        result = _dedup_hits(hits, max_pages=10)
        assert len(result) == 1
        assert result[0].title == "First"

    def test_empty_hits_returns_empty(self) -> None:
        result = _dedup_hits((), max_pages=10)
        assert result == []
