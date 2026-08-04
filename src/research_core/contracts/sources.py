"""
Source and Provenance contracts.

Source — describes the underlying resource (document, web page) independently
of any particular excerpt drawn from it.

Provenance — records the lineage of a specific evidence item: where it came
from, how it was retrieved, and how confident the extraction was.

EvidenceQuality — item-level quality assessment, distinct from the result-level
QualityDiagnostics.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from datetime import date, datetime

from research_core.contracts.common import (
    EMPTY_METADATA,
    DocumentId,
    Metadata,
    SourceId,
    SourceType,
    _to_proxy,
)
from research_core.exceptions import ContractValidationError


@dataclass(frozen=True)
class Source:
    """Description of an underlying source resource.

    A Source is the resource-level record (a document, a web page). It is
    separate from Provenance, which records the retrieval lineage of a specific
    evidence excerpt.

    Score fields (retrieval scores, quality scores) are on Provenance or
    EvidenceItem, not on Source, because the same source may have different
    relevance across different retrieval operations.
    """

    source_id: SourceId
    source_type: SourceType
    title: str = ""
    url: str | None = None
    document_id: DocumentId | None = None
    publisher: str | None = None
    author: str | None = None
    publication_date: date | None = None
    retrieved_at: datetime | None = None
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ContractValidationError("source_id must not be empty")
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class Provenance:
    """Retrieval and extraction lineage for a specific evidence item.

    Provenance records *how* a piece of evidence was obtained, not what the
    evidence says. Key distinctions:

    - retrieval_score: how well this item matched the retrieval query (engine
      signal); not a quality judgment.
    - extraction_confidence: how confident the extraction process was in
      producing the content field (a signal about process reliability).

    Neither should be confused with factual confidence or source authority.
    Both are normalized to [0.0, 1.0] when present.
    """

    source_id: SourceId
    source_type: SourceType
    retrieved_at: datetime
    document_id: DocumentId | None = None
    url: str | None = None
    provider: str | None = None
    retrieval_query: str | None = None
    retrieval_rank: int | None = None
    retrieval_score: float | None = None
    extraction_method: str | None = None
    extraction_confidence: float | None = None
    content_hash: str | None = None
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ContractValidationError("source_id must not be empty")

        if self.retrieved_at.tzinfo is None:
            raise ContractValidationError(
                "retrieved_at must be timezone-aware"
            )

        if self.retrieval_rank is not None and self.retrieval_rank < 0:
            raise ContractValidationError(
                f"retrieval_rank must be non-negative, got {self.retrieval_rank}"
            )

        _validate_unit_score("retrieval_score", self.retrieval_score)
        _validate_unit_score("extraction_confidence", self.extraction_confidence)

        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class EvidenceQuality:
    """Item-level quality assessment for a single evidence item.

    These dimensions describe the quality characteristics of one specific
    piece of evidence. They are distinct from the result-level QualityDiagnostics,
    which aggregate across the entire evidence pool.

    All scores are normalized to [0.0, 1.0] when present. None means the
    dimension was not assessed, not that it scored zero.
    """

    relevance: float | None = None
    authority: float | None = None
    recency: float | None = None
    extraction_confidence: float | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        for name, val in (
            ("relevance", self.relevance),
            ("authority", self.authority),
            ("recency", self.recency),
            ("extraction_confidence", self.extraction_confidence),
        ):
            _validate_unit_score(name, val)


def _validate_unit_score(name: str, value: float | None) -> None:
    """Raise ContractValidationError if *value* is outside [0.0, 1.0]."""
    if value is not None and not 0.0 <= value <= 1.0:
        raise ContractValidationError(
            f"{name} must be in [0.0, 1.0], got {value}"
        )
