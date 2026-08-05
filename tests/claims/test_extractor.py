"""Tests for DeterministicClaimExtractor — integration and determinism."""

from __future__ import annotations

import pytest

from research_core.claims import ClaimExtractionConfig, DeterministicClaimExtractor
from research_core.contracts.common import SourceType
from tests.claims.conftest import make_ranked_evidence

pytestmark = pytest.mark.claims

extractor = DeterministicClaimExtractor()


def test_empty_evidence_returns_valid_result() -> None:
    result = extractor.extract([])
    assert result.claims == ()
    assert result.diagnostics.input_evidence_count == 0
    assert result.diagnostics.claims_extracted == 0


def test_single_evidence_item() -> None:
    ranked = make_ranked_evidence(content="Revenue increased by 12%.")
    result = extractor.extract([ranked])
    assert len(result.claims) >= 1
    assert all(c.claim_text for c in result.claims)


def test_determinism_same_input_same_output() -> None:
    ranked = [
        make_ranked_evidence(
            content="Revenue increased by 12%. The policy may reduce emissions.",
            rank=1,
        ),
        make_ranked_evidence(
            evidence_id="ev-2",
            source_id="src-2",
            content="Higher prices led to lower demand.",
            rank=2,
        ),
    ]
    result1 = extractor.extract(ranked)
    result2 = extractor.extract(ranked)
    assert [c.claim_id for c in result1.claims] == [c.claim_id for c in result2.claims]


def test_reversed_input_order_same_claims() -> None:
    ev1 = make_ranked_evidence(
        evidence_id="ev-1", source_id="src-1",
        content="Revenue increased by 12%.", rank=1,
    )
    ev2 = make_ranked_evidence(
        evidence_id="ev-2", source_id="src-2",
        content="Costs fell significantly.", rank=2,
    )
    result1 = extractor.extract([ev1, ev2])
    result2 = extractor.extract([ev2, ev1])  # reversed list order but same ranks
    assert {c.claim_id for c in result1.claims} == {c.claim_id for c in result2.claims}


def test_low_ranked_evidence_not_skipped() -> None:
    # rank=10 should still be processed
    ranked = make_ranked_evidence(
        content="Revenue increased by 12%.",
        rank=10,
    )
    result = extractor.extract([ranked])
    assert len(result.claims) >= 1


def test_web_evidence_extracted() -> None:
    ranked = make_ranked_evidence(
        source_type=SourceType.WEB,
        content="According to the agency, costs increased by $2 million.",
    )
    result = extractor.extract([ranked])
    assert len(result.claims) >= 1


def test_include_rejections_true() -> None:
    cfg = ClaimExtractionConfig(include_rejections=True)
    ranked = make_ranked_evidence(
        content="Revenue increased by 12%. Overview. What caused this?"
    )
    result = extractor.extract([ranked], config=cfg)
    # Rejections tuple may or may not be non-empty — but should be populated
    # when something is rejected
    assert isinstance(result.rejections, tuple)


def test_include_rejections_false() -> None:
    cfg = ClaimExtractionConfig(include_rejections=False)
    ranked = make_ranked_evidence(
        content="Revenue increased by 12%. Overview."
    )
    result = extractor.extract([ranked], config=cfg)
    assert result.rejections == ()


def test_deduplication_disabled() -> None:
    cfg = ClaimExtractionConfig(deduplicate_exact=False)
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
    result = extractor.extract([seg1, seg2], config=cfg)
    texts = [c.claim_text for c in result.claims]
    # Without dedup, both claims should be present
    assert texts.count("Revenue increased by 12%.") >= 2


def test_meaning_preservation_negation() -> None:
    ranked = make_ranked_evidence(
        content="The intervention did not reduce mortality rates."
    )
    result = extractor.extract([ranked])
    assert any("not" in c.claim_text for c in result.claims)


def test_meaning_preservation_modal() -> None:
    ranked = make_ranked_evidence(
        content="Revenue may increase by up to 20% by 2030."
    )
    result = extractor.extract([ranked])
    assert any("may" in c.claim_text for c in result.claims)


def test_multiple_evidence_items() -> None:
    evidence = [
        make_ranked_evidence(
            evidence_id="ev-1", source_id="src-1",
            content="Revenue increased by 12%.", rank=1,
        ),
        make_ranked_evidence(
            evidence_id="ev-2", source_id="src-2",
            content="Costs fell significantly.", rank=2,
        ),
        make_ranked_evidence(
            evidence_id="ev-3", source_id="src-3",
            content="The policy may reduce emissions by 20% by 2030.", rank=3,
        ),
    ]
    result = extractor.extract(evidence)
    assert result.diagnostics.input_evidence_count == 3
    assert result.diagnostics.claims_extracted >= 3


def test_no_truth_score_on_claims() -> None:
    ranked = make_ranked_evidence(content="Revenue increased by 12%.")
    result = extractor.extract([ranked])
    for claim in result.claims:
        # No truth score should exist
        assert not hasattr(claim, "truth_score")
        assert not hasattr(claim, "verification_score")
        assert not hasattr(claim, "contradiction_status")


def test_protocol_conformance() -> None:
    from research_core.claims import ClaimExtractor

    assert isinstance(extractor, ClaimExtractor)
