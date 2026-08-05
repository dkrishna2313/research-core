"""Tests for modality detection."""

from __future__ import annotations

import pytest

from research_core.claims._classify import detect_modality
from research_core.claims.contracts import ClaimModality, ClaimQualifierKind

pytestmark = pytest.mark.claims


def test_may_is_possible() -> None:
    modality, qualifiers = detect_modality("The policy may reduce emissions.")
    assert modality == ClaimModality.POSSIBLE
    assert any("may" in q.text for q in qualifiers)


def test_might_is_possible() -> None:
    modality, _ = detect_modality("Costs might increase.")
    assert modality == ClaimModality.POSSIBLE


def test_could_is_possible() -> None:
    modality, _ = detect_modality("Demand could fall.")
    assert modality == ClaimModality.POSSIBLE


def test_likely_is_probable() -> None:
    modality, _ = detect_modality("Emissions likely declined.")
    assert modality == ClaimModality.PROBABLE


def test_expected_to_is_probable() -> None:
    modality, _ = detect_modality("Costs are expected to increase.")
    assert modality == ClaimModality.PROBABLE


def test_projected_to_is_probable() -> None:
    modality, _ = detect_modality("Revenue is projected to reach $10 billion.")
    assert modality == ClaimModality.PROBABLE


def test_must_is_required() -> None:
    modality, _ = detect_modality("Emissions must be reported.")
    assert modality == ClaimModality.REQUIRED


def test_required_to_is_required() -> None:
    modality, _ = detect_modality("Companies are required to disclose risks.")
    assert modality == ClaimModality.REQUIRED


def test_should_is_recommended() -> None:
    modality, _ = detect_modality("Companies should reduce emissions.")
    assert modality == ClaimModality.RECOMMENDED


def test_ought_to_is_recommended() -> None:
    modality, _ = detect_modality("Firms ought to report annually.")
    assert modality == ClaimModality.RECOMMENDED


def test_if_is_conditional() -> None:
    modality, _ = detect_modality("If emissions fall, costs will decline.")
    assert modality == ClaimModality.CONDITIONAL


def test_unless_is_conditional() -> None:
    modality, _ = detect_modality("Unless action is taken, emissions will rise.")
    assert modality == ClaimModality.CONDITIONAL


def test_subject_to_is_conditional() -> None:
    modality, _ = detect_modality("Subject to approval, the project will proceed.")
    assert modality == ClaimModality.CONDITIONAL


def test_plain_assertion_is_asserted() -> None:
    modality, qualifiers = detect_modality("Revenue increased by 12%.")
    assert modality == ClaimModality.ASSERTED
    assert qualifiers == []


def test_will_is_asserted_not_possible() -> None:
    # "will" is PREDICTIVE classification but ASSERTED modality
    modality, _ = detect_modality("Emissions will fall.")
    assert modality == ClaimModality.ASSERTED


def test_qualifier_text_preserved() -> None:
    modality, qualifiers = detect_modality("The policy may reduce emissions by 20%.")
    assert modality == ClaimModality.POSSIBLE
    assert len(qualifiers) >= 1
    qual = qualifiers[0]
    assert "may" in qual.text
    assert qual.kind == ClaimQualifierKind.MODAL


def test_qualifier_offsets_valid() -> None:
    text = "Costs may increase significantly."
    modality, qualifiers = detect_modality(text)
    assert modality == ClaimModality.POSSIBLE
    for q in qualifiers:
        assert q.start_char >= 0
        assert q.end_char > q.start_char
        assert q.end_char <= len(text)
        assert text[q.start_char : q.end_char] == q.text


def test_conditional_beats_possible() -> None:
    # "if" should win over "may" because CONDITIONAL has higher precedence
    modality, _ = detect_modality("If costs may increase, action is needed.")
    assert modality == ClaimModality.CONDITIONAL
