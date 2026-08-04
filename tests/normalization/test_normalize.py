"""Tests for the normalize_evidence function."""

from __future__ import annotations

import math

import pytest

pytestmark = pytest.mark.normalization

from research_core.exceptions import ContractValidationError  # noqa: E402
from research_core.normalization.config import NormalizationConfig, SegmentationConfig  # noqa: E402
from research_core.normalization.normalize import normalize_evidence  # noqa: E402
from tests.normalization.conftest import (  # noqa: E402
    make_knowledge_evidence,
    make_knowledge_source,
    make_source,
    make_web_evidence,
)


class TestNormalizeWebEvidence:
    def test_basic_normalization_returns_tuple(self) -> None:
        src = make_source()
        ev = make_web_evidence(source_id=src.source_id)
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        assert isinstance(result, tuple)
        assert len(result) == 1

    def test_provider_is_web(self) -> None:
        src = make_source()
        ev = make_web_evidence(source_id=src.source_id)
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        assert result[0].provider == "web"

    def test_provider_score_is_none_for_web(self) -> None:
        src = make_source()
        ev = make_web_evidence(source_id=src.source_id, score=None)
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        assert result[0].provider_score is None

    def test_rank_position_signal_rank1(self) -> None:
        src = make_source()
        ev = make_web_evidence(source_id=src.source_id, rank=1)
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        expected = 1.0 / (1.0 + math.log2(2))
        assert abs(result[0].normalized_retrieval_signal - expected) < 1e-9  # type: ignore[operator]

    def test_rank_position_signal_rank3(self) -> None:
        src = make_source()
        ev = make_web_evidence(source_id=src.source_id, rank=3)
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        expected = 1.0 / (1.0 + math.log2(4))
        assert abs(result[0].normalized_retrieval_signal - expected) < 1e-9  # type: ignore[operator]

    def test_no_rank_no_score_gives_none_signal(self) -> None:
        from datetime import UTC, datetime

        from research_core.contracts.common import SourceType
        from research_core.contracts.evidence import EvidenceItem
        from research_core.contracts.sources import EvidenceQuality, Provenance

        src = make_source()
        prov = Provenance(
            source_id=src.source_id,
            source_type=SourceType.WEB,
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
            retrieval_rank=None,
            retrieval_score=None,
        )
        ev = EvidenceItem(
            evidence_id="ev-no-rank",
            content="Content without rank or score.",
            source_id=src.source_id,
            provenance=prov,
            quality=EvidenceQuality(),
        )
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        assert result[0].normalized_retrieval_signal is None

    def test_content_length_set(self) -> None:
        src = make_source()
        content = "Hello world this is some content."
        ev = make_web_evidence(source_id=src.source_id, content=content)
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        assert result[0].content_length == len(content)

    def test_source_populated(self) -> None:
        src = make_source(source_id="src-abc")
        ev = make_web_evidence(source_id="src-abc")
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        assert result[0].source.source_id == "src-abc"


class TestNormalizeKnowledgeEvidence:
    def test_provider_is_knowledge(self) -> None:
        src = make_knowledge_source()
        ev = make_knowledge_evidence(source_id=src.source_id)
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        assert result[0].provider == "knowledge"

    def test_score_used_directly(self) -> None:
        src = make_knowledge_source()
        ev = make_knowledge_evidence(source_id=src.source_id, score=0.75)
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        assert result[0].provider_score == 0.75
        assert result[0].normalized_retrieval_signal == 0.75

    def test_zero_score_is_not_none(self) -> None:
        src = make_knowledge_source()
        ev = make_knowledge_evidence(source_id=src.source_id, score=0.0)
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        assert result[0].normalized_retrieval_signal == 0.0


class TestNormalizeSegmentation:
    def test_long_content_produces_multiple_normalized_items(self) -> None:
        cfg = NormalizationConfig(
            segmentation=SegmentationConfig(
                max_characters=500,
                target_characters=400,
                overlap_characters=50,
                minimum_segment_characters=50,
            )
        )
        src = make_source()
        content = ("word " * 300).strip()
        ev = make_web_evidence(source_id=src.source_id, content=content)
        result = normalize_evidence(sources=(src,), evidence=(ev,), config=cfg)
        assert len(result) > 1

    def test_segments_have_lineage_metadata(self) -> None:
        cfg = NormalizationConfig(
            segmentation=SegmentationConfig(
                max_characters=500,
                target_characters=400,
                overlap_characters=50,
                minimum_segment_characters=50,
            )
        )
        src = make_source()
        content = ("word " * 300).strip()
        ev = make_web_evidence(evidence_id="parent-ev", source_id=src.source_id, content=content)
        result = normalize_evidence(sources=(src,), evidence=(ev,), config=cfg)
        for ne in result:
            assert ne.parent_evidence_id == "parent-ev"
            assert ne.segment_index is not None
            assert ne.segment_count is not None

    def test_short_content_has_no_segment_metadata(self) -> None:
        src = make_source()
        ev = make_web_evidence(source_id=src.source_id, content="Short.")
        result = normalize_evidence(sources=(src,), evidence=(ev,))
        assert result[0].segment_index is None
        assert result[0].segment_count is None
        assert result[0].parent_evidence_id is None


class TestNormalizeValidation:
    def test_duplicate_source_ids_raises(self) -> None:
        src1 = make_source(source_id="src-dup")
        src2 = make_source(source_id="src-dup")
        ev = make_web_evidence(source_id="src-dup")
        with pytest.raises(ContractValidationError, match="Duplicate source_id"):
            normalize_evidence(sources=(src1, src2), evidence=(ev,))

    def test_duplicate_evidence_ids_raises(self) -> None:
        src = make_source()
        ev1 = make_web_evidence(evidence_id="ev-dup", source_id=src.source_id)
        ev2 = make_web_evidence(evidence_id="ev-dup", source_id=src.source_id)
        with pytest.raises(ContractValidationError, match="Duplicate evidence_id"):
            normalize_evidence(sources=(src,), evidence=(ev1, ev2))

    def test_unknown_source_id_raises(self) -> None:
        src = make_source(source_id="src-known")
        ev = make_web_evidence(evidence_id="ev-x", source_id="src-unknown")
        with pytest.raises(ContractValidationError, match="unknown source_id"):
            normalize_evidence(sources=(src,), evidence=(ev,))

    def test_empty_evidence_returns_empty(self) -> None:
        src = make_source()
        result = normalize_evidence(sources=(src,), evidence=())
        assert result == ()

    def test_empty_sources_and_evidence_ok(self) -> None:
        result = normalize_evidence(sources=(), evidence=())
        assert result == ()
