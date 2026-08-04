"""
Mapping functions from knowledge-layer types to research-core contracts.

All functions in this module accept knowledge-layer model objects and return
research-core contract objects. The knowledge package (dc-power-agent) must
be importable when these functions are called.

Score normalization:
    The knowledge-layer lexical retriever produces scores outside [0, 1].
    Maximum theoretical score (lexical mode, J8.3):

        lex_relevance_max  = 1.0 (full coverage) + 0.45 (intent boost) = 1.45
        metadata_factor_max = quality(1.2) × priority(1.1) × strategic(1.1) = 1.452
        max_score = 1.45 × 1.452 ≈ 2.1054

    normalize_score() divides by _LEXICAL_MAX_SCORE and clips to [0.0, 1.0].
"""

from __future__ import annotations

import types
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from research_core.contracts.common import EMPTY_METADATA, SourceType
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.sources import EvidenceQuality, Provenance, Source

if TYPE_CHECKING:
    from knowledge.models import KnowledgeMetadata as KLMetadata
    from knowledge.models import Source as KLSource
    from knowledge.retriever import RetrievedEvidence

_KNOWLEDGE_PROVIDER = "knowledge-layer"

# Maximum theoretical score from the knowledge-layer lexical retriever (J8.3).
# See module docstring for derivation.
_LEXICAL_MAX_SCORE: float = 2.1054


def normalize_score(score: float) -> float:
    """Normalize a knowledge-layer retrieval score to [0.0, 1.0]."""
    if score <= 0.0:
        return 0.0
    return min(1.0, round(score / _LEXICAL_MAX_SCORE, 6))


def map_source(ks: KLSource) -> Source:
    """Map a knowledge-layer Source to a research-core Source.

    retrieved_date (date) is promoted to timezone-aware datetime at midnight UTC.
    Fields without a direct counterpart in research-core Source are placed in
    metadata: domain, document_type, subtitle, organization, copyright,
    document_version, document_number, page_count.
    """
    retrieved_at: datetime | None = None
    if ks.retrieved_date is not None:
        retrieved_at = datetime(
            ks.retrieved_date.year,
            ks.retrieved_date.month,
            ks.retrieved_date.day,
            tzinfo=UTC,
        )

    extra: dict[str, object] = {}
    if ks.domain:
        extra["domain"] = ks.domain
    if ks.document_type:
        extra["document_type"] = ks.document_type
    if ks.subtitle:
        extra["subtitle"] = ks.subtitle
    if ks.organization:
        extra["organization"] = ks.organization
    if ks.copyright:
        extra["copyright"] = ks.copyright
    if ks.document_version:
        extra["document_version"] = ks.document_version
    if ks.document_number:
        extra["document_number"] = ks.document_number
    if ks.page_count is not None:
        extra["page_count"] = ks.page_count

    return Source(
        source_id=ks.source_id,
        source_type=SourceType.KNOWLEDGE,
        title=ks.title,
        url=ks.uri,
        publisher=ks.publisher,
        author=ks.author,
        publication_date=ks.publication_date,
        retrieved_at=retrieved_at,
        metadata=types.MappingProxyType(extra) if extra else EMPTY_METADATA,
    )


def map_evidence_quality(meta: KLMetadata) -> EvidenceQuality:
    """Map knowledge-layer KnowledgeMetadata quality signals to EvidenceQuality.

    KnowledgeMetadata uses a 1–5 scale for relevance, source_quality, and
    specificity. These are normalized linearly to [0.0, 1.0]:
        normalized = (score - 1.0) / 4.0

    KnowledgeMetadata.confidence is already in [0.0, 1.0] and maps directly
    to EvidenceQuality.extraction_confidence.
    """
    relevance = (meta.relevance_score - 1.0) / 4.0
    authority = (meta.source_quality_score - 1.0) / 4.0
    return EvidenceQuality(
        relevance=round(relevance, 4),
        authority=round(authority, 4),
        extraction_confidence=round(meta.confidence, 4),
    )


def map_evidence_item(
    item: RetrievedEvidence,
    query: str,
    retrieved_at: datetime,
) -> EvidenceItem | None:
    """Map a RetrievedEvidence item to a research-core EvidenceItem.

    Returns None when the item cannot be mapped (empty statement or evidence_id).
    The caller is responsible for filtering None values.

    source_id is taken from evidence.supporting_source_ids[0] when available,
    falling back to the evidence_id itself. The fallback ensures EvidenceItem
    is constructable even for orphaned evidence records.
    """
    ev = item.evidence
    meta = item.metadata

    if not ev.evidence_id or not ev.statement.strip():
        return None

    source_id = ev.supporting_source_ids[0] if ev.supporting_source_ids else ev.evidence_id

    provenance = Provenance(
        source_id=source_id,
        source_type=SourceType.KNOWLEDGE,
        retrieved_at=retrieved_at,
        retrieval_query=query,
        retrieval_rank=item.rank,
        retrieval_score=normalize_score(item.score),
        provider=_KNOWLEDGE_PROVIDER,
        content_hash=ev.content_fingerprint,
    )

    quality = map_evidence_quality(meta)

    locator: str | None = None
    if ev.page_number is not None:
        locator = f"page {ev.page_number}"

    extra: dict[str, object] = {}
    if ev.evidence_type:
        extra["evidence_type"] = ev.evidence_type
    if ev.entity:
        extra["entity"] = ev.entity
    if ev.category:
        extra["category"] = ev.category
    if ev.topics:
        extra["topics"] = list(ev.topics)
    if ev.chunk_id:
        extra["chunk_id"] = ev.chunk_id
    if item.source_domain:
        extra["source_domain"] = item.source_domain

    return EvidenceItem(
        evidence_id=ev.evidence_id,
        content=ev.statement,
        source_id=source_id,
        provenance=provenance,
        quality=quality,
        locator=locator,
        metadata=types.MappingProxyType(extra) if extra else EMPTY_METADATA,
    )
