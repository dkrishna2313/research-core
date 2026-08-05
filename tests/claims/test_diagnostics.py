"""Tests for claim extraction diagnostics — count reconciliation."""

from __future__ import annotations

import pytest

from research_core.claims import ClaimExtractionConfig, DeterministicClaimExtractor
from research_core.claims.contracts import ClaimModality, ClaimPolarity, ClaimType
from tests.claims.conftest import make_ranked_evidence

pytestmark = pytest.mark.claims

extractor = DeterministicClaimExtractor()


def test_zero_evidence_valid_result() -> None:
    result = extractor.extract([])
    diag = result.diagnostics
    assert diag.input_evidence_count == 0
    assert diag.claims_extracted == 0
    assert diag.claims_rejected == 0
    assert diag.duplicate_claims == 0
    assert diag.evidence_without_claims == 0


def test_claims_by_type_sum_equals_claims_extracted() -> None:
    evidence = [
        make_ranked_evidence(
            content=(
                "Revenue increased by 12%. The policy may reduce emissions."
                " Costs rose because supply fell."
            ),
            rank=1,
        )
    ]
    result = extractor.extract(evidence)
    diag = result.diagnostics
    type_sum = sum(diag.claims_by_type.values())
    assert type_sum == diag.claims_extracted


def test_claims_by_modality_sum_equals_claims_extracted() -> None:
    evidence = [
        make_ranked_evidence(
            content="Revenue increased by 12%. The policy may reduce emissions.",
            rank=1,
        )
    ]
    result = extractor.extract(evidence)
    diag = result.diagnostics
    mod_sum = sum(diag.claims_by_modality.values())
    assert mod_sum == diag.claims_extracted


def test_claims_by_polarity_sum_equals_claims_extracted() -> None:
    evidence = [
        make_ranked_evidence(
            content="Revenue increased by 12%. Costs did not fall.",
            rank=1,
        )
    ]
    result = extractor.extract(evidence)
    diag = result.diagnostics
    pol_sum = sum(diag.claims_by_polarity.values())
    assert pol_sum == diag.claims_extracted


def test_rejection_reasons_sum_equals_claims_rejected() -> None:
    evidence = [
        make_ranked_evidence(
            content="Revenue increased by 12%. Overview. What caused the increase? Costs fell.",
            rank=1,
        )
    ]
    cfg = ClaimExtractionConfig(include_rejections=True)
    result = extractor.extract(evidence, config=cfg)
    diag = result.diagnostics
    rej_sum = sum(diag.rejection_reasons.values())
    assert rej_sum == diag.claims_rejected


def test_input_count_correct() -> None:
    evidence = [
        make_ranked_evidence(evidence_id="ev-1", content="Revenue increased.", rank=1),
        make_ranked_evidence(evidence_id="ev-2", content="Costs fell.", rank=2, source_id="src-2"),
    ]
    result = extractor.extract(evidence)
    assert result.diagnostics.input_evidence_count == 2
    assert result.diagnostics.input_ranked_count == 2


def test_evidence_without_claims_counted() -> None:
    # A pure heading/boilerplate evidence item produces no claims
    evidence = [
        make_ranked_evidence(content="Overview", rank=1),
        make_ranked_evidence(
            evidence_id="ev-2", source_id="src-2",
            content="Revenue increased by 12%.", rank=2,
        ),
    ]
    result = extractor.extract(evidence)
    assert result.diagnostics.evidence_without_claims >= 1


def test_fingerprint_in_diagnostics() -> None:
    evidence = [make_ranked_evidence(content="Revenue increased.", rank=1)]
    cfg = ClaimExtractionConfig()
    result = extractor.extract(evidence, config=cfg)
    assert result.diagnostics.configuration_fingerprint == cfg.fingerprint


def test_all_claim_types_present_in_by_type() -> None:
    evidence = [make_ranked_evidence(content="Revenue increased.", rank=1)]
    result = extractor.extract(evidence)
    diag = result.diagnostics
    for ct in ClaimType:
        assert str(ct) in diag.claims_by_type


def test_all_modalities_present_in_by_modality() -> None:
    evidence = [make_ranked_evidence(content="Revenue increased.", rank=1)]
    result = extractor.extract(evidence)
    diag = result.diagnostics
    for m in ClaimModality:
        assert str(m) in diag.claims_by_modality


def test_all_polarities_present_in_by_polarity() -> None:
    evidence = [make_ranked_evidence(content="Revenue increased.", rank=1)]
    result = extractor.extract(evidence)
    diag = result.diagnostics
    for p in ClaimPolarity:
        assert str(p) in diag.claims_by_polarity
