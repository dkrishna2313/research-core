"""Shared fixtures for KnowledgeAdapter tests.

These fixtures create knowledge-layer model objects (Evidence, KnowledgeMetadata,
Source, RetrievedEvidence) for use in unit tests. The knowledge package must
be importable; tests skip automatically via pytest.importorskip when absent.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

knowledge = pytest.importorskip("knowledge", reason="knowledge package (dc-power-agent) required")

from knowledge.models import Evidence, KnowledgeMetadata  # noqa: E402
from knowledge.models import Source as KLSource  # noqa: E402
from knowledge.retriever import RetrievedEvidence  # noqa: E402


def make_kl_source(
    *,
    source_id: str = "abc123def456789012345678901234ab",
    uri: str = "https://example.com/doc.pdf",
    title: str = "Test Document",
    author: str | None = "Jane Doe",
    publisher: str | None = "Test Publisher",
    publication_date: date | None = date(2023, 6, 1),
    retrieved_date: date = date(2024, 1, 15),
    domain: str = "smr",
    document_type: str = "PDF",
    page_count: int | None = 50,
) -> KLSource:
    return KLSource(
        source_id=source_id,
        uri=uri,
        title=title,
        author=author,
        publisher=publisher,
        publication_date=publication_date,
        retrieved_date=retrieved_date,
        fingerprint="f" * 64,
        language="en",
        document_type=document_type,
        domain=domain,
        page_count=page_count,
        canonical_text="Sample canonical text for testing purposes.",
    )


def make_kl_evidence(
    *,
    evidence_id: str = "ev-unit-test-001",
    statement: str = "Small modular reactors offer significant deployment advantages.",
    evidence_type: str = "STRATEGIC",
    supporting_source_ids: list[str] | None = None,
    profile_ids: list[str] | None = None,
    page_number: int | None = 12,
    chunk_id: str | None = "chunk-001",
    entity: str = "SMR",
    category: str = "deployment",
    topics: list[str] | None = None,
    extraction_run_id: str = "run-test-001",
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        statement=statement,
        evidence_type=evidence_type,
        supporting_source_ids=(
            supporting_source_ids
            if supporting_source_ids is not None
            else ["abc123def456789012345678901234ab"]
        ),
        profile_ids=profile_ids if profile_ids is not None else ["smr-general"],
        page_number=page_number,
        chunk_id=chunk_id,
        entity=entity,
        category=category,
        topics=topics or ["deployment", "nuclear"],
        extraction_run_id=extraction_run_id,
    )


def make_kl_metadata(
    *,
    evidence_id: str = "ev-unit-test-001",
    confidence: float = 0.85,
    relevance_score: float = 4.0,
    source_quality_score: float = 3.5,
    specificity_score: float = 3.0,
    overall_score: float = 3.5,
    retrieval_priority: int = 3,
    strategic_value: float = 0.6,
    state: str = "ACTIVE",
    retrieval_enabled: bool = True,
) -> KnowledgeMetadata:
    return KnowledgeMetadata(
        evidence_id=evidence_id,
        confidence=confidence,
        relevance_score=relevance_score,
        source_quality_score=source_quality_score,
        specificity_score=specificity_score,
        overall_score=overall_score,
        retrieval_priority=retrieval_priority,
        strategic_value=strategic_value,
        state=state,
        retrieval_enabled=retrieval_enabled,
    )


def make_retrieved_evidence(
    *,
    evidence: Evidence | None = None,
    metadata: KnowledgeMetadata | None = None,
    score: float = 1.2,
    rank: int = 1,
    source: KLSource | None = None,
    source_domain: str = "smr",
    metadata_factor: float | None = 1.1,
) -> RetrievedEvidence:
    ev = evidence or make_kl_evidence()
    meta = metadata or make_kl_metadata(evidence_id=ev.evidence_id)
    return RetrievedEvidence(
        evidence=ev,
        metadata=meta,
        score=score,
        rank=rank,
        source=source,
        source_domain=source_domain,
        metadata_factor=metadata_factor,
    )


FIXED_TS = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def kl_source() -> KLSource:
    return make_kl_source()


@pytest.fixture
def kl_evidence() -> Evidence:
    return make_kl_evidence()


@pytest.fixture
def kl_metadata() -> KnowledgeMetadata:
    return make_kl_metadata()


@pytest.fixture
def retrieved_evidence(kl_evidence: Evidence, kl_metadata: KnowledgeMetadata) -> RetrievedEvidence:
    return make_retrieved_evidence(evidence=kl_evidence, metadata=kl_metadata)
