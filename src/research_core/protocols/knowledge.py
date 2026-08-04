"""
Knowledge retrieval protocol.

KnowledgeProvider is the boundary between the research engine and a local
knowledge store. Implementations may connect to vector databases, document
stores, or any retrieval backend.

The protocol is structural (typing.Protocol); no base class is required.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from research_core.contracts.common import EMPTY_METADATA, Metadata, ProfileId, _to_proxy
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.request import ResearchRequest
from research_core.contracts.sources import Source


@dataclass(frozen=True)
class KnowledgeRetrievalRequest:
    """Parameters for a single knowledge retrieval operation.

    query: the retrieval query string (may differ from the original question
           after rewriting or decomposition).
    max_results: maximum items to return; defaults to the parent request value.
    profiles: profile IDs that constrain the search scope; may be a subset
              of the parent request profiles.
    """

    query: str
    parent_request: ResearchRequest
    max_results: int | None = None
    profiles: tuple[ProfileId, ...] = field(default_factory=tuple)
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    @property
    def effective_max_results(self) -> int:
        if self.max_results is not None:
            return self.max_results
        return self.parent_request.max_knowledge_results


@dataclass(frozen=True)
class KnowledgeRetrievalResult:
    """Structured result of a knowledge retrieval operation.

    Bundles sources and evidence together so downstream consumers can populate
    ResearchResult.sources without a second lookup. This resolves the RC1
    contract defect where KnowledgeProvider returned only evidence with no
    reliable path to the corresponding Source objects.

    sources: Source records for all retrieved evidence items, deduplicated.
    evidence: retrieved EvidenceItem objects, ordered by relevance descending.
    """

    sources: tuple[Source, ...]
    evidence: tuple[EvidenceItem, ...]
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@runtime_checkable
class KnowledgeProvider(Protocol):
    """Structural protocol for a knowledge retrieval backend.

    Implementations do not need to inherit from this class. Any object that
    implements retrieve() with the correct signature satisfies the protocol.

    retrieve() must return a KnowledgeRetrievalResult; it must not return None.
    The result may have empty sources and evidence tuples when nothing matches.
    Implementations should raise ProviderUnavailableError or
    ProviderExecutionError on non-recoverable failures.
    """

    def retrieve(
        self, request: KnowledgeRetrievalRequest
    ) -> KnowledgeRetrievalResult:
        """Retrieve evidence and sources matching the retrieval request."""
        ...
