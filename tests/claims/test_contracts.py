"""Tests for RC5 claim contracts — immutability, validation, serialization."""

from __future__ import annotations

import dataclasses
import types

import pytest

from research_core.claims.contracts import (
    ClaimAttribution,
    ClaimExtractionDiagnostics,
    ClaimExtractionResult,
    ClaimModality,
    ClaimPolarity,
    ClaimQualifier,
    ClaimQualifierKind,
    ClaimScope,
    ClaimType,
    ExtractedClaim,
    QuantitativeExpression,
    TemporalExpression,
    TemporalKind,
)
from research_core.exceptions import ContractValidationError

pytestmark = pytest.mark.claims


# ---------------------------------------------------------------------------
# ClaimQualifier
# ---------------------------------------------------------------------------


def test_claim_qualifier_frozen() -> None:
    q = ClaimQualifier(text="may", kind=ClaimQualifierKind.MODAL, start_char=0, end_char=3)
    with pytest.raises(dataclasses.FrozenInstanceError):
        q.text = "must"  # type: ignore[misc]


def test_claim_qualifier_empty_text_rejected() -> None:
    with pytest.raises(ContractValidationError):
        ClaimQualifier(text="", kind=ClaimQualifierKind.MODAL, start_char=0, end_char=3)


def test_claim_qualifier_invalid_offsets_rejected() -> None:
    with pytest.raises(ContractValidationError):
        ClaimQualifier(text="may", kind=ClaimQualifierKind.MODAL, start_char=5, end_char=3)


def test_claim_qualifier_negative_start_rejected() -> None:
    with pytest.raises(ContractValidationError):
        ClaimQualifier(text="may", kind=ClaimQualifierKind.MODAL, start_char=-1, end_char=3)


# ---------------------------------------------------------------------------
# QuantitativeExpression
# ---------------------------------------------------------------------------


def test_quantitative_expression_frozen() -> None:
    q = QuantitativeExpression(
        text="12%", value_text="12", percentage=True, start_char=0, end_char=3
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        q.text = "20%"  # type: ignore[misc]


def test_quantitative_expression_empty_text_rejected() -> None:
    with pytest.raises(ContractValidationError):
        QuantitativeExpression(text="", value_text="12", start_char=0, end_char=3)


def test_quantitative_expression_invalid_offsets_rejected() -> None:
    with pytest.raises(ContractValidationError):
        QuantitativeExpression(text="12%", value_text="12", start_char=5, end_char=3)


def test_quantitative_expression_negative_start_rejected() -> None:
    with pytest.raises(ContractValidationError):
        QuantitativeExpression(text="12%", value_text="12", start_char=-1, end_char=3)


# ---------------------------------------------------------------------------
# TemporalExpression
# ---------------------------------------------------------------------------


def test_temporal_expression_frozen() -> None:
    t = TemporalExpression(text="2024", start_char=0, end_char=4, kind=TemporalKind.YEAR)
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.text = "2025"  # type: ignore[misc]


def test_temporal_expression_empty_text_rejected() -> None:
    with pytest.raises(ContractValidationError):
        TemporalExpression(text="", start_char=0, end_char=4, kind=TemporalKind.YEAR)


def test_temporal_expression_invalid_offsets_rejected() -> None:
    with pytest.raises(ContractValidationError):
        TemporalExpression(text="2024", start_char=5, end_char=4, kind=TemporalKind.YEAR)


# ---------------------------------------------------------------------------
# ClaimAttribution
# ---------------------------------------------------------------------------


def test_claim_attribution_frozen() -> None:
    a = ClaimAttribution(
        source_text="the agency",
        reporting_verb="said",
        attributed_text="costs rose",
        start_char=0,
        end_char=30,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.source_text = "the report"  # type: ignore[misc]


def test_claim_attribution_empty_source_rejected() -> None:
    with pytest.raises(ContractValidationError):
        ClaimAttribution(
            source_text="",
            reporting_verb="said",
            attributed_text="costs rose",
            start_char=0,
            end_char=20,
        )


def test_claim_attribution_invalid_offsets_rejected() -> None:
    with pytest.raises(ContractValidationError):
        ClaimAttribution(
            source_text="the agency",
            reporting_verb="said",
            attributed_text="costs rose",
            start_char=10,
            end_char=5,
        )


# ---------------------------------------------------------------------------
# ExtractedClaim
# ---------------------------------------------------------------------------


def _make_claim(**overrides: object) -> ExtractedClaim:
    defaults: dict[str, object] = {
        "claim_id": "clm-abc123",
        "claim_text": "Revenue increased by 12%.",
        "normalized_text": "Revenue increased by 12%.",
        "claim_type": ClaimType.QUANTITATIVE,
        "modality": ClaimModality.ASSERTED,
        "polarity": ClaimPolarity.POSITIVE,
        "scope": ClaimScope(),
        "qualifiers": (),
        "quantitative_expressions": (),
        "temporal_expressions": (),
        "attribution": None,
        "source_id": "src-1",
        "evidence_id": "ev-1",
        "parent_evidence_id": None,
        "segment_index": None,
        "evidence_start_char": 0,
        "evidence_end_char": 25,
        "sentence_index": 0,
        "clause_index": 0,
        "extractor": "DeterministicClaimExtractor",
        "extractor_version": "1",
    }
    defaults.update(overrides)
    return ExtractedClaim(**defaults)  # type: ignore[arg-type]


def test_extracted_claim_frozen() -> None:
    c = _make_claim()
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.claim_text = "modified"  # type: ignore[misc]


def test_extracted_claim_empty_claim_id_rejected() -> None:
    with pytest.raises(ContractValidationError):
        _make_claim(claim_id="")


def test_extracted_claim_empty_claim_text_rejected() -> None:
    with pytest.raises(ContractValidationError):
        _make_claim(claim_text="")


def test_extracted_claim_empty_normalized_text_rejected() -> None:
    with pytest.raises(ContractValidationError):
        _make_claim(normalized_text="")


def test_extracted_claim_empty_source_id_rejected() -> None:
    with pytest.raises(ContractValidationError):
        _make_claim(source_id="")


def test_extracted_claim_empty_evidence_id_rejected() -> None:
    with pytest.raises(ContractValidationError):
        _make_claim(evidence_id="")


def test_extracted_claim_invalid_offsets_rejected() -> None:
    with pytest.raises(ContractValidationError):
        _make_claim(evidence_start_char=10, evidence_end_char=5)


def test_extracted_claim_negative_start_rejected() -> None:
    with pytest.raises(ContractValidationError):
        _make_claim(evidence_start_char=-1)


def test_extracted_claim_negative_sentence_index_rejected() -> None:
    with pytest.raises(ContractValidationError):
        _make_claim(sentence_index=-1)


def test_extracted_claim_negative_clause_index_rejected() -> None:
    with pytest.raises(ContractValidationError):
        _make_claim(clause_index=-1)


def test_extracted_claim_negative_segment_index_rejected() -> None:
    with pytest.raises(ContractValidationError):
        _make_claim(segment_index=-1)


def test_extracted_claim_segment_index_zero_ok() -> None:
    c = _make_claim(segment_index=0)
    assert c.segment_index == 0


def test_extracted_claim_metadata_immutable() -> None:
    mutable = {"key": "value"}
    c = _make_claim(metadata=mutable)  # type: ignore[arg-type]
    assert isinstance(c.metadata, types.MappingProxyType)
    mutable["key"] = "changed"
    assert c.metadata["key"] == "value"


def test_extracted_claim_collections_are_tuples() -> None:
    c = _make_claim()
    assert isinstance(c.qualifiers, tuple)
    assert isinstance(c.quantitative_expressions, tuple)
    assert isinstance(c.temporal_expressions, tuple)


def test_extracted_claim_enum_values_are_strings() -> None:
    c = _make_claim()
    assert str(c.claim_type) == "quantitative"
    assert str(c.modality) == "asserted"
    assert str(c.polarity) == "positive"


# ---------------------------------------------------------------------------
# ClaimExtractionResult — empty is valid
# ---------------------------------------------------------------------------


def _make_diagnostics(**overrides: object) -> ClaimExtractionDiagnostics:
    import types as _types

    defaults: dict[str, object] = {
        "input_evidence_count": 0,
        "input_ranked_count": 0,
        "candidate_sentence_count": 0,
        "candidate_clause_count": 0,
        "claims_extracted": 0,
        "claims_rejected": 0,
        "duplicate_claims": 0,
        "evidence_without_claims": 0,
        "claims_by_type": _types.MappingProxyType({}),
        "claims_by_modality": _types.MappingProxyType({}),
        "claims_by_polarity": _types.MappingProxyType({}),
        "rejection_reasons": _types.MappingProxyType({}),
        "configuration_fingerprint": "abc123",
        "extractor_name": "DeterministicClaimExtractor",
        "extractor_version": "1",
    }
    defaults.update(overrides)
    return ClaimExtractionDiagnostics(**defaults)  # type: ignore[arg-type]


def test_empty_result_is_valid() -> None:
    result = ClaimExtractionResult(
        claims=(),
        duplicates=(),
        rejections=(),
        diagnostics=_make_diagnostics(),
    )
    assert result.claims == ()
    assert result.duplicates == ()
    assert result.rejections == ()


def test_result_metadata_immutable() -> None:
    mutable = {"x": 1}
    result = ClaimExtractionResult(
        claims=(),
        duplicates=(),
        rejections=(),
        diagnostics=_make_diagnostics(),
        metadata=mutable,  # type: ignore[arg-type]
    )
    assert isinstance(result.metadata, types.MappingProxyType)
    mutable["x"] = 99
    assert result.metadata["x"] == 1


# ---------------------------------------------------------------------------
# Enum serialization
# ---------------------------------------------------------------------------


def test_claim_type_serializes_to_string() -> None:
    assert ClaimType.QUANTITATIVE.value == "quantitative"
    assert ClaimType.CAUSAL.value == "causal"
    assert ClaimType.NORMATIVE.value == "normative"
    assert ClaimType.UNKNOWN.value == "unknown"


def test_claim_modality_serializes_to_string() -> None:
    assert ClaimModality.POSSIBLE.value == "possible"
    assert ClaimModality.REQUIRED.value == "required"
    assert ClaimModality.CONDITIONAL.value == "conditional"


def test_claim_polarity_serializes_to_string() -> None:
    assert ClaimPolarity.NEGATED.value == "negated"
    assert ClaimPolarity.MIXED.value == "mixed"
