"""Tests for claim-to-evidence lineage preservation."""

from __future__ import annotations

import pytest

from research_core.claims import DeterministicClaimExtractor
from tests.claims.conftest import make_ranked_evidence

pytestmark = pytest.mark.claims

extractor = DeterministicClaimExtractor()


def test_unsegmented_has_no_parent_or_segment() -> None:
    ranked = make_ranked_evidence(
        content="Revenue increased by 12%.",
        parent_evidence_id=None,
        segment_index=None,
    )
    result = extractor.extract([ranked])
    for claim in result.claims:
        assert claim.parent_evidence_id is None
        assert claim.segment_index is None


def test_segmented_has_parent_evidence_id() -> None:
    ranked = make_ranked_evidence(
        evidence_id="seg-001",
        content="Revenue increased by 12%.",
        parent_evidence_id="ev-parent",
        segment_index=0,
    )
    result = extractor.extract([ranked])
    for claim in result.claims:
        assert claim.parent_evidence_id == "ev-parent"
        assert claim.segment_index == 0


def test_evidence_id_matches_segment_not_parent() -> None:
    ranked = make_ranked_evidence(
        evidence_id="seg-001",
        content="Revenue increased by 12%.",
        parent_evidence_id="ev-parent",
        segment_index=0,
    )
    result = extractor.extract([ranked])
    for claim in result.claims:
        assert claim.evidence_id == "seg-001"
        assert claim.evidence_id != "ev-parent"


def test_source_id_preserved() -> None:
    ranked = make_ranked_evidence(
        source_id="source-abc",
        content="Revenue increased by 12%.",
    )
    result = extractor.extract([ranked])
    for claim in result.claims:
        assert claim.source_id == "source-abc"


def test_offsets_within_content_bounds() -> None:
    content = "Revenue increased by 12%. The policy may reduce emissions."
    ranked = make_ranked_evidence(content=content)
    result = extractor.extract([ranked])
    for claim in result.claims:
        assert claim.evidence_start_char >= 0
        assert claim.evidence_end_char <= len(content)
        assert claim.evidence_start_char < claim.evidence_end_char


def test_claim_text_matches_content_span_approximately() -> None:
    content = "Revenue increased by 12%."
    ranked = make_ranked_evidence(content=content)
    result = extractor.extract([ranked])
    assert len(result.claims) >= 1
    claim = result.claims[0]
    # The claim text should appear in the content
    assert claim.claim_text in content or content in claim.claim_text


def test_segment_index_preserved() -> None:
    ranked = make_ranked_evidence(
        evidence_id="seg-002",
        content="Costs fell significantly.",
        parent_evidence_id="ev-parent",
        segment_index=1,
    )
    result = extractor.extract([ranked])
    for claim in result.claims:
        assert claim.segment_index == 1


def test_original_ranked_evidence_not_mutated() -> None:
    ranked = make_ranked_evidence(
        content="Revenue increased by 12%.",
        rank=1,
    )
    original_rank = ranked.rank
    original_score = ranked.score
    extractor.extract([ranked])
    assert ranked.rank == original_rank
    assert ranked.score == original_score


def test_sentence_index_non_negative() -> None:
    ranked = make_ranked_evidence(
        content="Revenue increased. Costs fell. Demand rose.",
    )
    result = extractor.extract([ranked])
    for claim in result.claims:
        assert claim.sentence_index >= 0


def test_clause_index_non_negative() -> None:
    ranked = make_ranked_evidence(
        content="Revenue increased; costs fell.",
    )
    result = extractor.extract([ranked])
    for claim in result.claims:
        assert claim.clause_index >= 0


def test_extractor_name_and_version_set() -> None:
    ranked = make_ranked_evidence(content="Revenue increased by 12%.")
    result = extractor.extract([ranked])
    for claim in result.claims:
        assert claim.extractor == "DeterministicClaimExtractor"
        assert claim.extractor_version == "1"
