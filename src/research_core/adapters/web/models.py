"""
Internal data models for the web search adapter.

These models are NOT part of the public research-core API. They represent
intermediate state between the web provider and the research-core contracts.
Do not store instances of these models in public contracts or metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchHit:
    """One result from a web search provider.

    rank: 1-based position in the search results.
    url: result URL (may need normalization before use).
    title: page title from search result.
    snippet: short text excerpt from the search result.
    provider: name of the search provider (e.g. "duckduckgo").
    published_at: publication date string as returned by provider; may be None.
    """

    rank: int
    url: str
    title: str
    snippet: str = ""
    provider: str = ""
    published_at: str | None = None


@dataclass
class FetchedResource:
    """A fetched web page or document.

    requested_url: the URL passed to the fetcher.
    final_url: the URL after following redirects (may differ from requested_url).
    status_code: HTTP status code.
    content_type: Content-Type header value (may include charset).
    content: raw response body bytes (bounded to max_response_bytes).
    retrieved_at: timezone-aware datetime when the resource was fetched.
    encoding: declared encoding from Content-Type or charset header; may be None.
    truncated: True if the response body was truncated at max_response_bytes.
    """

    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    content: bytes
    retrieved_at: datetime
    encoding: str | None = None
    truncated: bool = False


@dataclass
class ExtractionResult:
    """Extracted text and metadata from a fetched resource.

    text: the main textual content extracted from the resource.
    title: document title if available; None if not extractable.
    extraction_method: name of the extractor used ("trafilatura", "pypdf", "docx", "plaintext").
    page_count: number of pages for multi-page documents (e.g. PDF); None for single-page.
    truncated: True if the extracted text was truncated.
    """

    text: str
    title: str | None
    extraction_method: str
    page_count: int | None = None
    truncated: bool = False
