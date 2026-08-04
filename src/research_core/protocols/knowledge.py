"""
Knowledge retrieval protocol.

KnowledgeProvider is the boundary between the research engine and a local
knowledge store. Implementations may connect to vector databases, document
stores, or any retrieval backend.

The protocol is structural (typing.Protocol); no base class is required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from research_core.contracts.common import EMPTY_METADATA, Metadata, ProfileId
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.request import ResearchRequest


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


@runtime_checkable
class KnowledgeProvider(Protocol):
    """Structural protocol for a knowledge retrieval backend.

    Implementations do not need to inherit from this class. Any object that
    implements retrieve() with the correct signature satisfies the protocol.

    retrieve() must return a (possibly empty) tuple; it must not return None.
    Implementations should raise ProviderUnavailableError or
    ProviderExecutionError on non-recoverable failures.
    """

    def retrieve(
        self, request: KnowledgeRetrievalRequest
    ) -> tuple[EvidenceItem, ...]:
        """Retrieve evidence items matching the retrieval request."""
        ...
