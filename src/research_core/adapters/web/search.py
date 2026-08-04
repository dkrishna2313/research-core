"""
Search client boundary for the web search adapter.

DdgsSearchClient wraps the ddgs (or legacy duckduckgo_search) package behind
the SearchClient protocol. The ddgs package is imported lazily at search() time.

Language note:
    DDGS uses a `region` parameter (e.g. "wt-wt" for worldwide, "us-en" for US
    English). It does not accept a plain BCP 47 language code. When a language
    is provided, it is passed directly as the region value. Callers should use
    region codes understood by DDGS (e.g. "us-en", "de-de"). Unknown values are
    passed through; DDGS will fall back to its default behavior.
"""

from __future__ import annotations

import traceback
from typing import Any, Protocol, runtime_checkable

from research_core.adapters.web.models import SearchHit
from research_core.exceptions import ProviderExecutionError, ProviderUnavailableError


@runtime_checkable
class SearchClient(Protocol):
    """Internal protocol for a web search provider."""

    def search(
        self,
        *,
        query: str,
        max_results: int,
        language: str | None,
        safe_search: str | None,
        timeout_seconds: float,
    ) -> tuple[SearchHit, ...]:
        """Execute a search and return ranked hits. Never raises on empty results."""
        ...


class DdgsSearchClient:
    """SearchClient backed by the ddgs (DuckDuckGo) package.

    Imports ddgs lazily on the first search() call. Falls back to the legacy
    duckduckgo_search package when ddgs is not installed.
    """

    _PROVIDER = "duckduckgo"

    def search(
        self,
        *,
        query: str,
        max_results: int,
        language: str | None,
        safe_search: str | None,
        timeout_seconds: float,
    ) -> tuple[SearchHit, ...]:
        """Search DuckDuckGo and return ranked SearchHit objects.

        Raises ProviderUnavailableError if neither ddgs nor duckduckgo_search
        is installed. Raises ProviderExecutionError on search failure.
        """
        DDGS = self._import_ddgs()

        region = language if language is not None else "wt-wt"
        safesearch = safe_search if safe_search is not None else "moderate"

        try:
            with DDGS() as ddgs:
                raw = list(
                    ddgs.text(
                        query,
                        region=region,
                        safesearch=safesearch,
                        max_results=max_results,
                    )
                )
        except Exception as exc:
            raise ProviderExecutionError(
                f"DuckDuckGo search failed for query {query!r}: {exc}\n"
                f"{traceback.format_exc()}"
            ) from exc

        hits = []
        for rank, item in enumerate(raw, start=1):
            url = (item.get("href") or "").strip()
            if not url:
                continue
            hits.append(
                SearchHit(
                    rank=rank,
                    url=url,
                    title=(item.get("title") or "").strip(),
                    snippet=(item.get("body") or "").strip(),
                    provider=self._PROVIDER,
                    published_at=item.get("published") or None,
                )
            )
        return tuple(hits)

    @staticmethod
    def _import_ddgs() -> Any:
        """Import and return the DDGS class, preferring ddgs over duckduckgo_search."""
        try:
            from ddgs import DDGS

            return DDGS
        except ImportError:
            pass
        try:
            from duckduckgo_search import DDGS as DuckDuckGoSearch

            return DuckDuckGoSearch
        except ImportError as exc:
            raise ProviderUnavailableError(
                "Neither ddgs nor duckduckgo_search is installed. "
                "Install with: pip install ddgs"
            ) from exc
