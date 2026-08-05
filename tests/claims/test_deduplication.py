"""Tests for exact claim deduplication policy."""

from __future__ import annotations

import pytest

from research_core.claims import DeterministicClaimExtractor
from research_core.claims._deduplicate import deduplicate_claims
from tests.claims.conftest import make_extracted_claim, make_ranked_evidence

pytestmark = pytest.mark.claims

extractor = DeterministicClaimExtractor()


def test_exact_duplicate_from_overlapping_segments_collapsed() -> None:
    # Two segments with same parent produce the same claim text
    seg1 = make_ranked_evidence(
        evidence_id="seg-001",
        content="Revenue increased by 12%.",
        source_id="src-1",
        parent_evidence_id="ev-parent",
        segment_index=0,
        rank=1,
    )
    seg2 = make_ranked_evidence(
        evidence_id="seg-002",
        content="Revenue increased by 12%.",
        source_id="src-1",
        parent_evidence_id="ev-parent",
        segment_index=1,
        rank=2,
    )
    result = extractor.extract([seg1, seg2])
    texts = [c.claim_text for c in result.claims]
    # The duplicate should be collapsed — only one claim with this text
    assert texts.count("Revenue increased by 12%.") == 1
    # And a duplicate record should exist
    assert len(result.duplicates) >= 1


def test_same_text_different_sources_retained_separately() -> None:
    # Same claim text, different sources — must NOT collapse
    ev1 = make_ranked_evidence(
        evidence_id="ev-1",
        source_id="src-1",
        content="Revenue increased by 12%.",
        rank=1,
    )
    ev2 = make_ranked_evidence(
        evidence_id="ev-2",
        source_id="src-2",  # different source
        content="Revenue increased by 12%.",
        rank=2,
    )
    result = extractor.extract([ev1, ev2])
    matching = [c for c in result.claims if "Revenue increased by 12" in c.claim_text]
    # Both should be retained
    assert len(matching) == 2


def test_different_numeric_values_retained_separately() -> None:
    ev1 = make_ranked_evidence(
        evidence_id="ev-1", source_id="src-1",
        content="Revenue was $10 million.", rank=1,
    )
    ev2 = make_ranked_evidence(
        evidence_id="ev-2", source_id="src-1",
        content="Revenue was $100 million.", rank=2,
    )
    result = extractor.extract([ev1, ev2])
    texts = [c.claim_text for c in result.claims]
    assert any("$10" in t or "10 million" in t for t in texts)
    assert any("$100" in t or "100 million" in t for t in texts)


def test_negated_vs_positive_retained_separately() -> None:
    ev1 = make_ranked_evidence(
        evidence_id="ev-1", source_id="src-1",
        content="The treatment reduced mortality.", rank=1,
    )
    ev2 = make_ranked_evidence(
        evidence_id="ev-2", source_id="src-1",
        content="The treatment did not reduce mortality.", rank=2,
    )
    result = extractor.extract([ev1, ev2])
    assert len(result.claims) >= 2


def test_duplicate_lineage_retained() -> None:
    seg1 = make_ranked_evidence(
        evidence_id="seg-001",
        content="Revenue increased by 12%.",
        source_id="src-1",
        parent_evidence_id="ev-parent",
        segment_index=0,
        rank=1,
    )
    seg2 = make_ranked_evidence(
        evidence_id="seg-002",
        content="Revenue increased by 12%.",
        source_id="src-1",
        parent_evidence_id="ev-parent",
        segment_index=1,
        rank=2,
    )
    result = extractor.extract([seg1, seg2])
    assert len(result.duplicates) >= 1
    dup = result.duplicates[0]
    assert dup.canonical_claim_id != ""
    assert dup.claim_id != dup.canonical_claim_id
    assert dup.similarity == 1.0


def test_canonical_selection_deterministic() -> None:
    seg1 = make_ranked_evidence(
        evidence_id="seg-001",
        content="Revenue increased by 12%.",
        source_id="src-1",
        parent_evidence_id="ev-parent",
        segment_index=0,
        rank=1,
    )
    seg2 = make_ranked_evidence(
        evidence_id="seg-002",
        content="Revenue increased by 12%.",
        source_id="src-1",
        parent_evidence_id="ev-parent",
        segment_index=1,
        rank=2,
    )
    result1 = extractor.extract([seg1, seg2])
    result2 = extractor.extract([seg2, seg1])  # reversed order
    ids1 = {c.claim_id for c in result1.claims}
    ids2 = {c.claim_id for c in result2.claims}
    assert ids1 == ids2


def test_deduplication_low_level_api() -> None:
    # Test deduplicate_claims directly
    c1 = make_extracted_claim(
        claim_id="clm-a",
        normalized_text="Revenue increased.",
        evidence_id="ev-1",
        source_id="src-1",
        parent_evidence_id="ev-parent",
        segment_index=0,
        evidence_start_char=0,
        evidence_end_char=19,
    )
    c2 = make_extracted_claim(
        claim_id="clm-b",
        normalized_text="Revenue increased.",
        evidence_id="ev-2",
        source_id="src-1",
        parent_evidence_id="ev-parent",
        segment_index=1,
        evidence_start_char=0,
        evidence_end_char=19,
    )
    canonical, dups = deduplicate_claims([c1, c2])
    assert len(canonical) == 1
    assert len(dups) == 1
