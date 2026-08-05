"""Tests for the evidence segmenter."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.normalization

from research_core.normalization.config import SegmentationConfig  # noqa: E402
from research_core.normalization.segmenter import segment_evidence  # noqa: E402
from tests.normalization.conftest import make_web_evidence  # noqa: E402


def _long_content(n: int = 10000) -> str:
    """Generate long content with paragraph structure."""
    paragraphs = [f"Paragraph {i}: " + ("word " * 50).strip() for i in range(n // 300 + 1)]
    return "\n\n".join(paragraphs)


class TestSegmenterShortContent:
    def test_short_content_returns_single_item(self) -> None:
        item = make_web_evidence(content="Short content.")
        result = segment_evidence(item)
        assert len(result) == 1
        assert result[0] is item

    def test_exactly_max_chars_returns_single_item(self) -> None:
        cfg = SegmentationConfig(max_characters=100, target_characters=80, overlap_characters=10,
                                  minimum_segment_characters=10)
        item = make_web_evidence(content="x" * 100)
        result = segment_evidence(item, cfg)
        assert len(result) == 1
        assert result[0] is item

    def test_one_char_over_max_gets_segmented(self) -> None:
        cfg = SegmentationConfig(
            max_characters=100,
            target_characters=80,
            overlap_characters=10,
            minimum_segment_characters=1,
        )
        item = make_web_evidence(content="x" * 101)
        result = segment_evidence(item, cfg)
        assert len(result) >= 2


class TestSegmenterLongContent:
    def test_long_content_produces_multiple_segments(self) -> None:
        cfg = SegmentationConfig(
            max_characters=500,
            target_characters=400,
            overlap_characters=50,
            minimum_segment_characters=50,
        )
        item = make_web_evidence(content=_long_content(1500))
        result = segment_evidence(item, cfg)
        assert len(result) > 1

    def test_all_segments_are_evidence_items(self) -> None:
        from research_core.contracts.evidence import EvidenceItem

        cfg = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                  minimum_segment_characters=50)
        item = make_web_evidence(content=_long_content(1500))
        result = segment_evidence(item, cfg)
        for seg in result:
            assert isinstance(seg, EvidenceItem)

    def test_segment_ids_are_different(self) -> None:
        cfg = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                  minimum_segment_characters=50)
        item = make_web_evidence(content=_long_content(1500))
        result = segment_evidence(item, cfg)
        ids = [seg.evidence_id for seg in result]
        assert len(ids) == len(set(ids))

    def test_segment_ids_differ_from_parent_id(self) -> None:
        cfg = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                  minimum_segment_characters=50)
        item = make_web_evidence(content=_long_content(1500))
        result = segment_evidence(item, cfg)
        for seg in result:
            assert seg.evidence_id != item.evidence_id

    def test_segment_ids_are_stable(self) -> None:
        """Same input → same segment IDs."""
        cfg = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                  minimum_segment_characters=50)
        item = make_web_evidence(content=_long_content(1500))
        result1 = segment_evidence(item, cfg)
        result2 = segment_evidence(item, cfg)
        assert [s.evidence_id for s in result1] == [s.evidence_id for s in result2]

    def test_segment_ids_start_with_seg_prefix(self) -> None:
        cfg = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                  minimum_segment_characters=50)
        item = make_web_evidence(content=_long_content(1500))
        result = segment_evidence(item, cfg)
        for seg in result:
            assert seg.evidence_id.startswith("seg-")

    def test_segments_preserve_source_id(self) -> None:
        cfg = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                  minimum_segment_characters=50)
        item = make_web_evidence(source_id="src-xyz", content=_long_content(1500))
        result = segment_evidence(item, cfg)
        for seg in result:
            assert seg.source_id == "src-xyz"

    def test_segments_preserve_provenance(self) -> None:
        cfg = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                  minimum_segment_characters=50)
        item = make_web_evidence(rank=3, content=_long_content(1500))
        result = segment_evidence(item, cfg)
        for seg in result:
            assert seg.provenance.retrieval_rank == 3

    def test_segments_metadata_has_lineage(self) -> None:
        cfg = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                  minimum_segment_characters=50)
        item = make_web_evidence(evidence_id="parent-ev", content=_long_content(1500))
        result = segment_evidence(item, cfg)
        for seg in result:
            assert seg.metadata["parent_evidence_id"] == "parent-ev"
            assert "segment_index" in seg.metadata
            assert "segment_count" in seg.metadata

    def test_segment_count_consistent(self) -> None:
        cfg = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                  minimum_segment_characters=50)
        item = make_web_evidence(content=_long_content(1500))
        result = segment_evidence(item, cfg)
        total = len(result)
        for seg in result:
            assert seg.metadata["segment_count"] == total

    def test_version_change_changes_ids(self) -> None:
        cfg1 = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                   minimum_segment_characters=50, version="1")
        cfg2 = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                   minimum_segment_characters=50, version="2")
        item = make_web_evidence(content=_long_content(1500))
        r1 = segment_evidence(item, cfg1)
        r2 = segment_evidence(item, cfg2)
        assert r1[0].evidence_id != r2[0].evidence_id

    def test_locator_annotated(self) -> None:
        cfg = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                  minimum_segment_characters=50)
        item = make_web_evidence(content=_long_content(1500))
        result = segment_evidence(item, cfg)
        assert "segment 1/" in result[0].locator  # type: ignore[operator]

    def test_locator_includes_parent_locator(self) -> None:
        from datetime import UTC, datetime

        from research_core.contracts.common import SourceType
        from research_core.contracts.evidence import EvidenceItem
        from research_core.contracts.sources import EvidenceQuality, Provenance

        content = _long_content(1500)
        prov = Provenance(
            source_id="src-001",
            source_type=SourceType.WEB,
            retrieved_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        item = EvidenceItem(
            evidence_id="ev-loc",
            content=content,
            source_id="src-001",
            provenance=prov,
            quality=EvidenceQuality(),
            locator="page 5",
        )
        cfg = SegmentationConfig(max_characters=500, target_characters=400, overlap_characters=50,
                                  minimum_segment_characters=50)
        result = segment_evidence(item, cfg)
        assert result[0].locator is not None
        assert "page 5" in result[0].locator


class TestSegmenterContentIdentity:
    """Content hash is part of the segment ID (RC4 hardening)."""

    def test_content_change_changes_segment_id(self) -> None:
        cfg = SegmentationConfig(
            max_characters=500, target_characters=400, overlap_characters=0,
            minimum_segment_characters=50,
        )
        item_a = make_web_evidence(evidence_id="ev-x", content=("A" * 600))
        item_b = make_web_evidence(evidence_id="ev-x", content=("B" * 600))
        segs_a = segment_evidence(item_a, cfg)
        segs_b = segment_evidence(item_b, cfg)
        assert segs_a[0].evidence_id != segs_b[0].evidence_id

    def test_segment_id_stable_across_calls(self) -> None:
        cfg = SegmentationConfig(
            max_characters=500, target_characters=400, overlap_characters=0,
            minimum_segment_characters=50,
        )
        item = make_web_evidence(content=("word " * 400))
        segs1 = segment_evidence(item, cfg)
        segs2 = segment_evidence(item, cfg)
        assert [s.evidence_id for s in segs1] == [s.evidence_id for s in segs2]

    def test_content_hash_stored_in_metadata(self) -> None:
        import hashlib

        cfg = SegmentationConfig(
            max_characters=500, target_characters=400, overlap_characters=0,
            minimum_segment_characters=50,
        )
        item = make_web_evidence(content=("word " * 400))
        segs = segment_evidence(item, cfg)
        for seg in segs:
            assert "content_hash" in seg.metadata
            expected = hashlib.sha256(seg.content.encode()).hexdigest()
            assert seg.metadata["content_hash"] == expected

    def test_original_evidence_not_mutated(self) -> None:
        cfg = SegmentationConfig(
            max_characters=500, target_characters=400, overlap_characters=0,
            minimum_segment_characters=50,
        )
        item = make_web_evidence(evidence_id="ev-orig", content=("word " * 400))
        segment_evidence(item, cfg)
        assert item.evidence_id == "ev-orig"

    def test_same_content_different_parent_id_gives_different_seg_id(self) -> None:
        cfg = SegmentationConfig(
            max_characters=500, target_characters=400, overlap_characters=0,
            minimum_segment_characters=50,
        )
        content = "word " * 400
        item_a = make_web_evidence(evidence_id="ev-aaa", content=content)
        item_b = make_web_evidence(evidence_id="ev-bbb", content=content)
        segs_a = segment_evidence(item_a, cfg)
        segs_b = segment_evidence(item_b, cfg)
        assert segs_a[0].evidence_id != segs_b[0].evidence_id


class TestSegmenterParagraphSplitting:
    def test_paragraph_boundaries_respected(self) -> None:
        cfg = SegmentationConfig(
            max_characters=200,
            target_characters=150,
            overlap_characters=20,
            minimum_segment_characters=10,
            preserve_paragraphs=True,
        )
        content = ("A" * 80) + "\n\n" + ("B" * 80) + "\n\n" + ("C" * 80)
        item = make_web_evidence(content=content)
        result = segment_evidence(item, cfg)
        # Each paragraph should be in its own segment approximately
        assert len(result) > 1
        assert all(seg.content.strip() for seg in result)
