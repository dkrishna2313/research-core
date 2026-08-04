"""
Web search and retrieval protocol.

WebSearchProvider is the boundary between the research engine and external
web search services. Implementations may connect to search APIs, browser
automation, or page fetching backends.

The protocol is structural (typing.Protocol); no base class is required.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from research_core.contracts.common import EMPTY_METADATA, Metadata, _to_proxy
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.request import ResearchRequest
from research_core.contracts.sources import Source
from research_core.exceptions import ContractValidationError


@dataclass(frozen=True)
class WebSearchRequest:
    """Parameters for a single web search operation.

    query: the search query string (must not be empty or whitespace-only).
    max_results: maximum search result items to return; defaults to the
                 parent request value.
    max_pages: maximum page bodies to fetch and extract from; defaults to
               the parent request value.
    language: BCP 47 language code for results; defaults to "en".
    """

    query: str
    parent_request: ResearchRequest
    max_results: int | None = None
    max_pages: int | None = None
    language: str | None = None
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ContractValidationError(
                "WebSearchRequest.query must not be empty or whitespace-only"
            )
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))

    @property
    def effective_max_results(self) -> int:
        if self.max_results is not None:
            return self.max_results
        return self.parent_request.max_web_results

    @property
    def effective_max_pages(self) -> int:
        return self.max_pages if self.max_pages is not None else self.parent_request.max_web_pages

    @property
    def effective_language(self) -> str:
        return self.language if self.language is not None else self.parent_request.language


@dataclass(frozen=True)
class WebSearchResult:
    """Structured result of a web search operation.

    Bundles sources and evidence so downstream consumers can populate
    ResearchResult.sources without a second lookup. This resolves the
    protocol defect where WebSearchProvider returned paired tuples with
    no clean separation of sources and evidence.

    sources: Source records for all fetched pages, deduplicated by URL.
    evidence: EvidenceItem objects extracted from pages, ordered by search rank.
    """

    sources: tuple[Source, ...]
    evidence: tuple[EvidenceItem, ...]
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@runtime_checkable
class WebSearchProvider(Protocol):
    """Structural protocol for a web search and retrieval backend.

    search() returns a WebSearchResult bundling both sources and evidence.
    Sources are deduplicated; evidence items are ordered by search rank.

    Implementations should raise ProviderUnavailableError or
    ProviderExecutionError on non-recoverable failures.
    Zero search matches must return an empty WebSearchResult, not raise.
    """

    def search(self, request: WebSearchRequest) -> WebSearchResult:
        """Search the web and return structured sources and evidence."""
        ...
