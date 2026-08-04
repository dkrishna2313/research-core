"""Shared fixtures and factories for normalization tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from research_core.contracts.common import SourceType
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.sources import EvidenceQuality, Provenance, Source

FIXED_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def make_source(
    source_id: str = "src-001",
    source_type: SourceType = SourceType.WEB,
    title: str = "Test Source",
    url: str | None = "https://example.com/page",
) -> Source:
    return Source(
        source_id=source_id,
        source_type=source_type,
        title=title,
        url=url,
    )


def make_web_evidence(
    evidence_id: str = "ev-001",
    source_id: str = "src-001",
    content: str = "This is some web evidence content for testing purposes.",
    rank: int = 1,
    score: float | None = None,
    extraction_confidence: float | None = None,
    quality: EvidenceQuality | None = None,
) -> EvidenceItem:
    provenance = Provenance(
        source_id=source_id,
        source_type=SourceType.WEB,
        retrieved_at=FIXED_TS,
        provider="duckduckgo",
        retrieval_rank=rank,
        retrieval_score=score,
        extraction_method="trafilatura",
        extraction_confidence=extraction_confidence,
    )
    return EvidenceItem(
        evidence_id=evidence_id,
        content=content,
        source_id=source_id,
        provenance=provenance,
        quality=quality or EvidenceQuality(),
    )


def make_knowledge_evidence(
    evidence_id: str = "ev-k01",
    source_id: str = "src-k01",
    content: str = "This is some knowledge evidence content for testing.",
    rank: int | None = 1,
    score: float | None = 0.85,
    quality: EvidenceQuality | None = None,
) -> EvidenceItem:
    provenance = Provenance(
        source_id=source_id,
        source_type=SourceType.KNOWLEDGE,
        retrieved_at=FIXED_TS,
        provider="knowledge",
        retrieval_rank=rank,
        retrieval_score=score,
        extraction_method="text",
        extraction_confidence=0.9,
    )
    return EvidenceItem(
        evidence_id=evidence_id,
        content=content,
        source_id=source_id,
        provenance=provenance,
        quality=quality
        or EvidenceQuality(relevance=0.8, authority=0.7, recency=0.6, extraction_confidence=0.9),
    )


def make_knowledge_source(
    source_id: str = "src-k01",
    title: str = "Knowledge Document",
) -> Source:
    return make_source(source_id=source_id, source_type=SourceType.KNOWLEDGE, title=title, url=None)


@pytest.fixture
def web_source() -> Source:
    return make_source()


@pytest.fixture
def knowledge_source() -> Source:
    return make_knowledge_source()


@pytest.fixture
def web_evidence(web_source: Source) -> EvidenceItem:
    return make_web_evidence(source_id=web_source.source_id)


@pytest.fixture
def knowledge_evidence(knowledge_source: Source) -> EvidenceItem:
    return make_knowledge_evidence(source_id=knowledge_source.source_id)
