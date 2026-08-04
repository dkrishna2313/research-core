"""
Web search and retrieval protocol.

WebSearchProvider is the boundary between the research engine and external
web search services. Implementations may connect to search APIs, browser
automation, or page fetching backends.

The protocol is structural (typing.Protocol); no base class is required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from research_core.contracts.common import EMPTY_METADATA, Metadata
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.request import ResearchRequest
from research_core.contracts.sources import Source


@dataclass(frozen=True)
class WebSearchRequest:
    """Parameters for a single web search operation.

    query: the search query string.
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


@runtime_checkable
class WebSearchProvider(Protocol):
    """Structural protocol for a web search and retrieval backend.

    search() returns a tuple of (Source, EvidenceItem) pairs — one per
    extracted evidence item.  A single page may yield multiple items.

    Implementations should raise ProviderUnavailableError or
    ProviderExecutionError on non-recoverable failures.
    """

    def search(
        self, request: WebSearchRequest
    ) -> tuple[tuple[Source, EvidenceItem], ...]:
        """Search the web and return paired (source, evidence) results."""
        ...
