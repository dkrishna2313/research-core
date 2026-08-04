"""Tests for WebCache."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.web

from research_core.adapters.web.cache import WebCache  # noqa: E402


class TestWebCacheMissAndHit:
    def test_cache_miss_returns_none(self, tmp_path: Path) -> None:
        cache = WebCache(tmp_path / "cache")
        assert cache.get("https://example.com") is None

    def test_cache_hit_after_set(self, tmp_path: Path) -> None:
        cache = WebCache(tmp_path / "cache")
        cache.set("https://example.com", {"title": "Example", "text": "content"})
        result = cache.get("https://example.com")
        assert result is not None
        assert result["title"] == "Example"

    def test_cache_creates_directory(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "subdir" / "cache"
        cache = WebCache(cache_dir)
        cache.set("https://example.com", {"x": 1})
        assert cache_dir.exists()

    def test_different_urls_different_keys(self, tmp_path: Path) -> None:
        cache = WebCache(tmp_path / "cache")
        cache.set("https://example.com/a", {"val": "a"})
        cache.set("https://example.com/b", {"val": "b"})
        assert cache.get("https://example.com/a") == {"val": "a"}
        assert cache.get("https://example.com/b") == {"val": "b"}


class TestWebCacheBytesHandling:
    def test_bytes_content_survives_roundtrip(self, tmp_path: Path) -> None:
        cache = WebCache(tmp_path / "cache")
        data: dict[str, object] = {
            "url": "https://example.com",
            "content": b"<html>content</html>",
        }
        cache.set("https://example.com", data)
        result = cache.get("https://example.com")
        assert result is not None
        assert result["content"] == b"<html>content</html>"

    def test_non_bytes_fields_preserved(self, tmp_path: Path) -> None:
        cache = WebCache(tmp_path / "cache")
        data: dict[str, object] = {
            "title": "My Title",
            "status_code": 200,
            "content": b"bytes here",
        }
        cache.set("https://example.com", data)
        result = cache.get("https://example.com")
        assert result is not None
        assert result["title"] == "My Title"
        assert result["status_code"] == 200


class TestWebCacheAtomicWrite:
    def test_no_tmp_file_remains(self, tmp_path: Path) -> None:
        cache = WebCache(tmp_path / "cache")
        cache.set("https://example.com", {"x": 1})
        tmp_files = list((tmp_path / "cache").glob("*.tmp"))
        assert tmp_files == []


class TestWebCacheInvalidate:
    def test_invalidate_removes_entry(self, tmp_path: Path) -> None:
        cache = WebCache(tmp_path / "cache")
        cache.set("https://example.com", {"x": 1})
        removed = cache.invalidate("https://example.com")
        assert removed is True
        assert cache.get("https://example.com") is None

    def test_invalidate_returns_false_on_miss(self, tmp_path: Path) -> None:
        cache = WebCache(tmp_path / "cache")
        result = cache.invalidate("https://example.com/not-cached")
        assert result is False


class TestWebCacheCorruption:
    def test_corrupted_file_returns_none(self, tmp_path: Path) -> None:
        cache = WebCache(tmp_path / "cache")
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        import hashlib

        key = hashlib.sha256(b"https://example.com").hexdigest()[:16]
        (cache_dir / f"{key}.json").write_text("NOT VALID JSON", encoding="utf-8")
        result = cache.get("https://example.com")
        assert result is None


class TestWebCacheKeyDeterminism:
    def test_same_url_same_key_path(self, tmp_path: Path) -> None:
        cache = WebCache(tmp_path / "cache")
        p1 = cache._key_path("https://example.com")
        p2 = cache._key_path("https://example.com")
        assert p1 == p2

    def test_different_urls_different_key_paths(self, tmp_path: Path) -> None:
        cache = WebCache(tmp_path / "cache")
        p1 = cache._key_path("https://example.com/a")
        p2 = cache._key_path("https://example.com/b")
        assert p1 != p2
