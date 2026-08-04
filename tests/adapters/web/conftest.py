"""Shared fixtures and factory functions for web adapter tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from research_core.adapters.web.fetch import HostResolver
from research_core.adapters.web.models import ExtractionResult, FetchedResource, SearchHit


class FakeResolver:
    """Test double for HostResolver. Always returns a configurable list of IPs."""

    def __init__(self, addresses: list[str] | None = None) -> None:
        self._addresses = addresses if addresses is not None else ["1.2.3.4"]

    def resolve(self, hostname: str, port: int) -> list[str]:
        return self._addresses

    def __call__(self, hostname: str, port: int) -> list[str]:  # HostResolver duck type
        return self._addresses


assert isinstance(FakeResolver(), HostResolver)


@pytest.fixture
def fake_resolver() -> FakeResolver:
    return FakeResolver()

FIXED_TS = datetime(2024, 3, 1, 10, 0, 0, tzinfo=UTC)


def make_search_hit(
    *,
    rank: int = 1,
    url: str = "https://example.com/page",
    title: str = "Test Page",
    snippet: str = "A test snippet about the topic.",
    provider: str = "duckduckgo",
    published_at: str | None = None,
) -> SearchHit:
    return SearchHit(
        rank=rank,
        url=url,
        title=title,
        snippet=snippet,
        provider=provider,
        published_at=published_at,
    )


def make_fetched_resource(
    *,
    requested_url: str = "https://example.com/page",
    final_url: str = "https://example.com/page",
    status_code: int = 200,
    content_type: str = "text/html; charset=utf-8",
    content: bytes = b"<html><head><title>Test</title></head><body>Test content.</body></html>",
    retrieved_at: datetime | None = None,
    encoding: str | None = "utf-8",
    truncated: bool = False,
) -> FetchedResource:
    return FetchedResource(
        requested_url=requested_url,
        final_url=final_url,
        status_code=status_code,
        content_type=content_type,
        content=content,
        retrieved_at=retrieved_at or FIXED_TS,
        encoding=encoding,
        truncated=truncated,
    )


def make_extraction_result(
    *,
    text: str = "Some extracted text content for testing purposes.",
    title: str | None = "Test Page",
    method: str = "trafilatura",
    page_count: int | None = None,
    truncated: bool = False,
) -> ExtractionResult:
    return ExtractionResult(
        text=text,
        title=title,
        extraction_method=method,
        page_count=page_count,
        truncated=truncated,
    )


@pytest.fixture
def search_hit() -> SearchHit:
    return make_search_hit()


@pytest.fixture
def fetched_resource() -> FetchedResource:
    return make_fetched_resource()


@pytest.fixture
def extraction_result() -> ExtractionResult:
    return make_extraction_result()
