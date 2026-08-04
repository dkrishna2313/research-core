"""Tests for knowledge-layer → research-core mapping functions."""

from __future__ import annotations

import types
from datetime import UTC, date

import pytest

knowledge = pytest.importorskip("knowledge", reason="knowledge package (dc-power-agent) required")

from research_core.adapters.knowledge.mapping import (  # noqa: E402
    _LEXICAL_MAX_SCORE,
    map_evidence_item,
    map_evidence_quality,
    map_source,
    normalize_score,
)
from research_core.contracts.common import SourceType  # noqa: E402
from research_core.contracts.sources import Source  # noqa: E402

from .conftest import (  # noqa: E402
    FIXED_TS,
    make_kl_evidence,
    make_kl_metadata,
    make_kl_source,
    make_retrieved_evidence,
)


class TestNormalizeScore:
    def test_zero_returns_zero(self) -> None:
        assert normalize_score(0.0) == 0.0

    def test_negative_returns_zero(self) -> None:
        assert normalize_score(-1.0) == 0.0

    def test_max_score_normalizes_to_one(self) -> None:
        assert normalize_score(_LEXICAL_MAX_SCORE) == 1.0

    def test_above_max_clips_to_one(self) -> None:
        assert normalize_score(_LEXICAL_MAX_SCORE * 2) == 1.0

    def test_midpoint_is_in_range(self) -> None:
        result = normalize_score(1.0)
        assert 0.0 < result < 1.0

    def test_proportional(self) -> None:
        half = normalize_score(_LEXICAL_MAX_SCORE / 2)
        assert abs(half - 0.5) < 0.001


class TestMapSource:
    def test_source_id_preserved(self) -> None:
        ks = make_kl_source(source_id="abc123def456789012345678901234ab")
        src = map_source(ks)
        assert src.source_id == "abc123def456789012345678901234ab"

    def test_source_type_is_knowledge(self) -> None:
        src = map_source(make_kl_source())
        assert src.source_type == SourceType.KNOWLEDGE

    def test_uri_maps_to_url(self) -> None:
        ks = make_kl_source(uri="https://example.com/report.pdf")
        src = map_source(ks)
        assert src.url == "https://example.com/report.pdf"

    def test_title_preserved(self) -> None:
        ks = make_kl_source(title="Advanced SMR Report")
        src = map_source(ks)
        assert src.title == "Advanced SMR Report"

    def test_author_preserved(self) -> None:
        ks = make_kl_source(author="Dr. Smith")
        src = map_source(ks)
        assert src.author == "Dr. Smith"

    def test_publisher_preserved(self) -> None:
        ks = make_kl_source(publisher="IAEA")
        src = map_source(ks)
        assert src.publisher == "IAEA"

    def test_publication_date_preserved(self) -> None:
        ks = make_kl_source(publication_date=date(2023, 3, 15))
        src = map_source(ks)
        assert src.publication_date == date(2023, 3, 15)

    def test_retrieved_date_becomes_timezone_aware_datetime(self) -> None:
        ks = make_kl_source(retrieved_date=date(2024, 1, 15))
        src = map_source(ks)
        assert src.retrieved_at is not None
        assert src.retrieved_at.tzinfo is not None
        assert src.retrieved_at.year == 2024
        assert src.retrieved_at.month == 1
        assert src.retrieved_at.day == 15
        assert src.retrieved_at.hour == 0
        assert src.retrieved_at.tzinfo == UTC

    def test_domain_in_metadata(self) -> None:
        ks = make_kl_source(domain="smr")
        src = map_source(ks)
        assert src.metadata["domain"] == "smr"

    def test_document_type_in_metadata(self) -> None:
        ks = make_kl_source(document_type="PDF")
        src = map_source(ks)
        assert src.metadata["document_type"] == "PDF"

    def test_page_count_in_metadata(self) -> None:
        ks = make_kl_source(page_count=42)
        src = map_source(ks)
        assert src.metadata["page_count"] == 42

    def test_metadata_is_mapping_proxy(self) -> None:
        src = map_source(make_kl_source())
        assert isinstance(src.metadata, types.MappingProxyType)

    def test_returns_frozen_source(self) -> None:
        src = map_source(make_kl_source())
        assert isinstance(src, Source)
        with pytest.raises((AttributeError, TypeError)):
            src.title = "mutated"  # type: ignore[misc]


class TestMapEvidenceQuality:
    def test_min_scores_map_to_zero(self) -> None:
        meta = make_kl_metadata(
            relevance_score=1.0,
            source_quality_score=1.0,
            confidence=0.0,
        )
        q = map_evidence_quality(meta)
        assert q.relevance == 0.0
        assert q.authority == 0.0
        assert q.extraction_confidence == 0.0

    def test_max_scores_map_to_one(self) -> None:
        meta = make_kl_metadata(
            relevance_score=5.0,
            source_quality_score=5.0,
            confidence=1.0,
        )
        q = map_evidence_quality(meta)
        assert q.relevance == 1.0
        assert q.authority == 1.0
        assert q.extraction_confidence == 1.0

    def test_midpoint_maps_to_half(self) -> None:
        meta = make_kl_metadata(
            relevance_score=3.0,
            source_quality_score=3.0,
            confidence=0.5,
        )
        q = map_evidence_quality(meta)
        assert abs(q.relevance - 0.5) < 0.001
        assert abs(q.authority - 0.5) < 0.001
        assert abs(q.extraction_confidence - 0.5) < 0.001

    def test_scores_in_unit_range(self) -> None:
        meta = make_kl_metadata(relevance_score=4.0, source_quality_score=2.5)
        q = map_evidence_quality(meta)
        assert 0.0 <= q.relevance <= 1.0
        assert 0.0 <= q.authority <= 1.0


class TestMapEvidenceItem:
    def test_evidence_id_preserved(self) -> None:
        item = make_retrieved_evidence(evidence=make_kl_evidence(evidence_id="ev-test-001"))
        result = map_evidence_item(item, "test query", FIXED_TS)
        assert result is not None
        assert result.evidence_id == "ev-test-001"

    def test_statement_becomes_content(self) -> None:
        ev = make_kl_evidence(statement="Nuclear plants provide baseload power.")
        item = make_retrieved_evidence(evidence=ev)
        result = map_evidence_item(item, "energy", FIXED_TS)
        assert result is not None
        assert result.content == "Nuclear plants provide baseload power."

    def test_source_id_from_supporting_sources(self) -> None:
        ev = make_kl_evidence(supporting_source_ids=["src-001", "src-002"])
        item = make_retrieved_evidence(evidence=ev)
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.source_id == "src-001"

    def test_source_id_fallback_to_evidence_id(self) -> None:
        ev = make_kl_evidence(evidence_id="ev-orphan", supporting_source_ids=[])
        item = make_retrieved_evidence(evidence=ev)
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.source_id == "ev-orphan"

    def test_provenance_retrieved_at_is_passed_value(self) -> None:
        item = make_retrieved_evidence()
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.provenance.retrieved_at == FIXED_TS

    def test_provenance_retrieved_at_is_timezone_aware(self) -> None:
        item = make_retrieved_evidence()
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.provenance.retrieved_at.tzinfo is not None

    def test_provenance_query_preserved(self) -> None:
        item = make_retrieved_evidence()
        result = map_evidence_item(item, "SMR deployment risks", FIXED_TS)
        assert result is not None
        assert result.provenance.retrieval_query == "SMR deployment risks"

    def test_provenance_rank_preserved(self) -> None:
        item = make_retrieved_evidence(rank=3)
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.provenance.retrieval_rank == 3

    def test_retrieval_score_normalized(self) -> None:
        item = make_retrieved_evidence(score=_LEXICAL_MAX_SCORE)
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.provenance.retrieval_score == pytest.approx(1.0, abs=0.001)

    def test_retrieval_score_in_unit_range(self) -> None:
        item = make_retrieved_evidence(score=1.0)
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        score = result.provenance.retrieval_score
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_page_number_becomes_locator(self) -> None:
        ev = make_kl_evidence(page_number=7)
        item = make_retrieved_evidence(evidence=ev)
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.locator == "page 7"

    def test_no_page_number_locator_is_none(self) -> None:
        ev = make_kl_evidence(page_number=None)
        item = make_retrieved_evidence(evidence=ev)
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.locator is None

    def test_evidence_type_in_metadata(self) -> None:
        ev = make_kl_evidence(evidence_type="STRATEGIC")
        item = make_retrieved_evidence(evidence=ev)
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.metadata["evidence_type"] == "STRATEGIC"

    def test_topics_in_metadata(self) -> None:
        ev = make_kl_evidence(topics=["nuclear", "grid"])
        item = make_retrieved_evidence(evidence=ev)
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.metadata["topics"] == ["nuclear", "grid"]

    def test_source_domain_in_metadata(self) -> None:
        item = make_retrieved_evidence(source_domain="smr")
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.metadata["source_domain"] == "smr"

    def test_empty_statement_returns_none(self) -> None:
        ev = make_kl_evidence(statement="   ")
        item = make_retrieved_evidence(evidence=ev)
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is None

    def test_provider_is_knowledge_layer(self) -> None:
        item = make_retrieved_evidence()
        result = map_evidence_item(item, "query", FIXED_TS)
        assert result is not None
        assert result.provenance.provider == "knowledge-layer"
