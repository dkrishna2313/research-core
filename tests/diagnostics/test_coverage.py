"""
Tests for compute_coverage() structural diagnostics.
"""

from __future__ import annotations

import pytest

from research_core.analysis.aggregate import compute_coverage
from tests.diagnostics.conftest import make_claim, make_ranked_evidence, make_source


@pytest.mark.diagnostics
class TestComputeCoverageEmpty:
    def test_no_sources_no_evidence_no_claims(self) -> None:
        cov = compute_coverage([], [], [])
        assert cov.source_count == 0
        assert cov.evidence_count == 0
        assert cov.claim_count == 0
        assert cov.claim_coverage_ratio is None
        assert cov.evidence_utilization_ratio is None

    def test_no_claims_ratios_none_or_zero(self) -> None:
        sources = [make_source()]
        evidence = [make_ranked_evidence()]
        cov = compute_coverage(sources, evidence, [])
        assert cov.claim_coverage_ratio is None
        assert cov.evidence_utilization_ratio == 0.0


@pytest.mark.diagnostics
class TestComputeCoverageBasic:
    def test_one_source_one_evidence_one_claim(self) -> None:
        src = make_source()
        ev = make_ranked_evidence(evidence_id="ev-1", source_id="src-1")
        cl = make_claim(claim_id="clm-1", evidence_id="ev-1", source_id="src-1")
        cov = compute_coverage([src], [ev], [cl])
        assert cov.source_count == 1
        assert cov.evidence_count == 1
        assert cov.claim_count == 1
        assert cov.claims_with_evidence == 1
        assert cov.claims_without_evidence == 0
        assert cov.evidence_with_claims == 1
        assert cov.evidence_without_claims == 0
        assert cov.claim_coverage_ratio == 1.0
        assert cov.evidence_utilization_ratio == 1.0

    def test_claim_referencing_unknown_evidence(self) -> None:
        src = make_source()
        ev = make_ranked_evidence(evidence_id="ev-known")
        cl = make_claim(claim_id="clm-1", evidence_id="ev-unknown", source_id="src-1")
        cov = compute_coverage([src], [ev], [cl])
        assert cov.claims_without_evidence == 1
        assert cov.claim_coverage_ratio == 0.0

    def test_evidence_without_claims(self) -> None:
        src = make_source()
        ev1 = make_ranked_evidence(evidence_id="ev-1")
        ev2 = make_ranked_evidence(evidence_id="ev-2", rank=2)
        cl = make_claim(evidence_id="ev-1")
        cov = compute_coverage([src], [ev1, ev2], [cl])
        assert cov.evidence_without_claims == 1
        assert cov.evidence_utilization_ratio == 0.5

    def test_sources_without_claims(self) -> None:
        src1 = make_source(source_id="src-1")
        src2 = make_source(source_id="src-2")
        ev = make_ranked_evidence(source_id="src-1")
        cl = make_claim(source_id="src-1", evidence_id="ev-1")
        cov = compute_coverage([src1, src2], [ev], [cl])
        assert cov.sources_with_claims == 1
        assert cov.sources_without_claims == 1

    def test_ranked_evidence_count_matches_evidence_count(self) -> None:
        src = make_source()
        ev_list = [make_ranked_evidence(evidence_id=f"ev-{i}", rank=i + 1) for i in range(3)]
        cov = compute_coverage([src], ev_list, [])
        assert cov.ranked_evidence_count == 3
        assert cov.evidence_count == 3


@pytest.mark.diagnostics
class TestComputeCoverageSegmented:
    def test_segmented_evidence_counted(self) -> None:
        src = make_source()
        parent = make_ranked_evidence(evidence_id="ev-parent", rank=1)
        seg1 = make_ranked_evidence(
            evidence_id="ev-seg-1",
            rank=2,
            parent_evidence_id="ev-parent",
            segment_index=0,
        )
        seg2 = make_ranked_evidence(
            evidence_id="ev-seg-2",
            rank=3,
            parent_evidence_id="ev-parent",
            segment_index=1,
        )
        cov = compute_coverage([src], [parent, seg1, seg2], [])
        assert cov.segmented_evidence_count == 2
        assert cov.unique_parent_evidence_count == 1
