"""Tests for Source, Provenance, and EvidenceQuality contracts."""

from __future__ import annotations

import types
from datetime import datetime

import pytest

from research_core.contracts.common import SourceType
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.exceptions import ContractValidationError
from tests.conftest import FIXED_TS, make_provenance, make_source


class TestSource:
    def test_minimal_construction(self) -> None:
        s = make_source(source_id="s1", source_type=SourceType.WEB)
        assert s.source_id == "s1"
        assert s.source_type == SourceType.WEB

    def test_empty_source_id_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="source_id"):
            Source(source_id="", source_type=SourceType.KNOWLEDGE)

    def test_whitespace_source_id_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            Source(source_id="   ", source_type=SourceType.KNOWLEDGE)

    def test_metadata_wrapped(self) -> None:
        s = Source(source_id="s1", source_type=SourceType.KNOWLEDGE, metadata={"k": "v"})
        assert isinstance(s.metadata, types.MappingProxyType)

    def test_is_frozen(self) -> None:
        s = make_source()
        with pytest.raises((AttributeError, TypeError)):
            s.title = "new"  # type: ignore[misc]


class TestProvenance:
    def test_minimal_construction(self) -> None:
        p = make_provenance()
        assert p.source_id == "src-1"
        assert p.retrieved_at == FIXED_TS

    def test_naive_retrieved_at_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="timezone"):
            Provenance(
                source_id="s1",
                source_type=SourceType.KNOWLEDGE,
                retrieved_at=datetime(2024, 1, 1),
            )

    def test_negative_retrieval_rank_rejected(self) -> None:
        with pytest.raises(ContractValidationError, match="retrieval_rank"):
            make_provenance(retrieval_rank=-1)

    def test_retrieval_score_out_of_range_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_provenance(retrieval_score=1.5)

    def test_extraction_confidence_out_of_range_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            make_provenance(extraction_confidence=-0.1)

    def test_valid_scores_accepted(self) -> None:
        p = make_provenance(retrieval_score=0.75, extraction_confidence=1.0)
        assert p.retrieval_score == 0.75
        assert p.extraction_confidence == 1.0

    def test_is_frozen(self) -> None:
        p = make_provenance()
        with pytest.raises((AttributeError, TypeError)):
            p.provider = "other"  # type: ignore[misc]


class TestEvidenceQuality:
    def test_all_none_is_valid(self) -> None:
        q = EvidenceQuality()
        assert q.relevance is None
        assert q.authority is None

    def test_scores_in_range_accepted(self) -> None:
        q = EvidenceQuality(relevance=0.8, authority=0.6, recency=1.0, extraction_confidence=0.0)
        assert q.relevance == 0.8

    def test_relevance_out_of_range_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            EvidenceQuality(relevance=1.1)

    def test_authority_out_of_range_rejected(self) -> None:
        with pytest.raises(ContractValidationError):
            EvidenceQuality(authority=-0.5)

    def test_none_is_not_zero(self) -> None:
        q = EvidenceQuality(relevance=None)
        assert q.relevance is None
        q2 = EvidenceQuality(relevance=0.0)
        assert q2.relevance == 0.0
        assert q.relevance != q2.relevance
