"""
WebSearchAdapter — WebSearchProvider backed by DuckDuckGo and requests/trafilatura.

Architecture:
    WebSearchAdapter coordinates three injectable boundaries:
    - SearchClient: executes the search query (default: DdgsSearchClient)
    - PageFetcher: downloads pages (default: RequestsFetcher)
    - ContentExtractor: extracts text (default: CompositeExtractor pipeline)

    An optional WebCache may be provided for disk-backed page caching.

Partial failures:
    A single page fetch or extraction failure does not abort the search.
    Failed pages are skipped and the remaining results are returned.
    A total search-provider failure raises ProviderUnavailableError or
    ProviderExecutionError.

Thread safety:
    WebSearchAdapter instances are not thread-safe. Each thread should use
    its own instance. The injected clients and fetcher are also assumed
    not to be shared across threads.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from research_core.adapters.web.cache import WebCache
from research_core.adapters.web.extract import (
    CompositeExtractor,
    ContentExtractor,
    default_extractor,
)
from research_core.adapters.web.mapping import (
    map_evidence_item,
    map_source,
    normalize_url,
    source_id_for_url,
    validate_scheme,
)
from research_core.adapters.web.models import FetchedResource, SearchHit
from research_core.contracts.sources import Source
from research_core.exceptions import ProviderExecutionError, ProviderUnavailableError
from research_core.protocols.web import WebSearchRequest, WebSearchResult

if TYPE_CHECKING:
    from research_core.adapters.web.fetch import PageFetcher
    from research_core.adapters.web.search import SearchClient

LOGGER = logging.getLogger(__name__)


class WebSearchAdapter:
    """WebSearchProvider backed by DuckDuckGo search and requests/trafilatura page fetching.

    Parameters
    ----------
    search_client:
        Injectable SearchClient. Defaults to DdgsSearchClient (lazy ddgs import).
    page_fetcher:
        Injectable PageFetcher. Defaults to RequestsFetcher (lazy requests import).
    extractor:
        Injectable ContentExtractor. Defaults to CompositeExtractor pipeline.
    cache:
        Optional WebCache for disk-backed page caching. None disables caching.
    timeout_seconds:
        Timeout for both search and page fetch operations.
    max_response_bytes:
        Maximum response body size in bytes (default: 10 MB).
    """

    def __init__(
        self,
        *,
        search_client: SearchClient | None = None,
        page_fetcher: PageFetcher | None = None,
        extractor: ContentExtractor | CompositeExtractor | None = None,
        cache: WebCache | None = None,
        timeout_seconds: float = 20.0,
        max_response_bytes: int = 10 * 1024 * 1024,
    ) -> None:
        self._search_client = search_client
        self._page_fetcher = page_fetcher
        self._extractor = extractor
        self._cache = cache
        self._timeout_seconds = timeout_seconds
        self._max_response_bytes = max_response_bytes

    @staticmethod
    def is_available() -> bool:
        """Return True if a DuckDuckGo search client is importable."""
        try:
            import ddgs  # noqa: F401

            return True
        except ImportError:
            pass
        try:
            import duckduckgo_search  # noqa: F401

            return True
        except ImportError:
            return False

    def search(self, request: WebSearchRequest) -> WebSearchResult:
        """Search the web and return structured sources and evidence.

        Steps:
        1. Execute search query via search client.
        2. Deduplicate and validate hit URLs; limit to max_pages.
        3. Fetch each page (with optional cache).
        4. Extract content from each page.
        5. Map to research-core Source and EvidenceItem contracts.
        6. Return WebSearchResult with sources and evidence.

        A single page failure is logged and skipped — it does not abort the search.
        Total search provider failure raises ProviderUnavailableError or
        ProviderExecutionError.

        Zero search hits returns an empty WebSearchResult (not a failure).
        """
        retrieved_at = datetime.now(UTC)
        query = request.query
        max_results = request.effective_max_results
        max_pages = request.effective_max_pages
        language = request.effective_language

        # Stage 1: search
        client = self._get_search_client()
        try:
            hits = client.search(
                query=query,
                max_results=max_results,
                language=language if language != "en" else None,
                safe_search="moderate",
                timeout_seconds=self._timeout_seconds,
            )
        except (ProviderUnavailableError, ProviderExecutionError):
            raise
        except Exception as exc:
            raise ProviderExecutionError(
                f"web search failed for query {query!r}: {exc}"
            ) from exc

        LOGGER.debug(
            "web search: query=%r hits=%d max_results=%d max_pages=%d",
            query,
            len(hits),
            max_results,
            max_pages,
        )

        # Stage 2: deduplicate and validate URLs, limit to max_pages
        deduplicated = _dedup_hits(hits, max_pages)

        # Stage 3-5: fetch, extract, map
        sources: list[Source] = []
        evidence_items = []
        seen_source_ids: set[str] = set()
        fetcher = self._get_fetcher()
        extractor = self._get_extractor()

        for hit in deduplicated:
            try:
                resource = self._fetch_with_cache(hit.url, fetcher)
                if resource.status_code >= 400:
                    LOGGER.debug(
                        "skipping page: status=%d url=%r", resource.status_code, hit.url
                    )
                    continue

                extraction = extractor.extract(resource)
                if not extraction.text.strip():
                    continue

                src = map_source(hit, resource, extraction, retrieved_at)
                ev = map_evidence_item(hit, resource, extraction, query, retrieved_at)

                src_id = source_id_for_url(resource.final_url)
                if src_id not in seen_source_ids:
                    sources.append(src)
                    seen_source_ids.add(src_id)
                evidence_items.append(ev)

            except (ProviderUnavailableError, ProviderExecutionError) as exc:
                LOGGER.debug("skipping page: %s url=%r", exc, hit.url)
                continue
            except Exception as exc:
                LOGGER.debug("skipping page (unexpected): %s url=%r", exc, hit.url)
                continue

        return WebSearchResult(
            sources=tuple(sources),
            evidence=tuple(evidence_items),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_search_client(self) -> SearchClient:
        if self._search_client is not None:
            return self._search_client
        from research_core.adapters.web.search import DdgsSearchClient

        return DdgsSearchClient()

    def _get_fetcher(self) -> PageFetcher:
        if self._page_fetcher is not None:
            return self._page_fetcher
        from research_core.adapters.web.fetch import RequestsFetcher

        return RequestsFetcher(max_response_bytes=self._max_response_bytes)

    def _get_extractor(self) -> ContentExtractor | CompositeExtractor:
        if self._extractor is not None:
            return self._extractor
        return default_extractor()

    def _fetch_with_cache(self, url: str, fetcher: PageFetcher) -> FetchedResource:
        if self._cache is not None:
            cached = self._cache.get(url)
            if cached is not None:
                return _resource_from_cache(url, cached)

        resource = fetcher.fetch(url, timeout_seconds=self._timeout_seconds)

        if self._cache is not None and resource.status_code < 400:
            self._cache.set(url, _resource_to_cache(resource))

        return resource


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _dedup_hits(hits: tuple[SearchHit, ...], max_pages: int) -> list[SearchHit]:
    """Deduplicate search hits by normalized URL, limit to max_pages.

    Invalid/unsupported URLs are silently dropped.
    Order follows the original search rank.
    """
    seen: set[str] = set()
    result: list[SearchHit] = []
    for hit in hits:
        try:
            norm = normalize_url(hit.url)
            validate_scheme(norm)
        except Exception:
            continue
        if norm not in seen:
            seen.add(norm)
            result.append(hit)
        if len(result) >= max_pages:
            break
    return result


def _resource_to_cache(resource: FetchedResource) -> dict[str, object]:
    """Serialize a FetchedResource to a cache-safe dict."""
    return {
        "final_url": resource.final_url,
        "status_code": resource.status_code,
        "content_type": resource.content_type,
        "content": resource.content,
        "retrieved_at": resource.retrieved_at.isoformat(),
        "encoding": resource.encoding,
        "truncated": resource.truncated,
    }


def _resource_from_cache(requested_url: str, data: dict[str, object]) -> FetchedResource:
    """Reconstruct a FetchedResource from a cached dict."""
    from datetime import datetime

    raw_ts = data.get("retrieved_at", "")
    try:
        retrieved_at = datetime.fromisoformat(str(raw_ts))
        if retrieved_at.tzinfo is None:
            retrieved_at = retrieved_at.replace(tzinfo=UTC)
    except Exception:
        retrieved_at = datetime.now(UTC)

    content = data.get("content", b"")
    if not isinstance(content, bytes):
        content = b""

    raw_status = data.get("status_code", 200)
    return FetchedResource(
        requested_url=requested_url,
        final_url=str(data.get("final_url", requested_url)),
        status_code=int(raw_status) if isinstance(raw_status, int) else 200,
        content_type=str(data.get("content_type", "")),
        content=content,
        retrieved_at=retrieved_at,
        encoding=data.get("encoding") if isinstance(data.get("encoding"), str) else None,  # type: ignore[arg-type]
        truncated=bool(data.get("truncated", False)),
    )
