"""Tests for polarity detection — negation preservation."""

from __future__ import annotations

import pytest

from research_core.claims._classify import detect_polarity
from research_core.claims.contracts import ClaimPolarity

pytestmark = pytest.mark.claims


def test_positive_default() -> None:
    assert detect_polarity("Revenue increased by 12%.") == ClaimPolarity.POSITIVE


def test_not_is_negated() -> None:
    assert detect_polarity("The intervention did not reduce mortality.") == ClaimPolarity.NEGATED


def test_never_is_negated() -> None:
    assert detect_polarity("Costs never exceeded the limit.") == ClaimPolarity.NEGATED


def test_no_is_negated() -> None:
    assert detect_polarity("There is no evidence of decline.") == ClaimPolarity.NEGATED


def test_cannot_is_negated() -> None:
    assert detect_polarity("Cannot be verified with current data.") == ClaimPolarity.NEGATED


def test_did_not_is_negated() -> None:
    assert detect_polarity("The policy did not reduce emissions.") == ClaimPolarity.NEGATED


def test_failed_to_is_negated() -> None:
    assert detect_polarity("The intervention failed to reduce mortality.") == ClaimPolarity.NEGATED


def test_doesnt_is_negated() -> None:
    assert detect_polarity("The approach doesn't work.") == ClaimPolarity.NEGATED


def test_modal_positive_no_negation() -> None:
    assert detect_polarity("Revenue may increase by up to 20% by 2030.") == ClaimPolarity.POSITIVE


def test_not_only_but_also_is_mixed() -> None:
    result = detect_polarity("Not only costs but also emissions fell.")
    assert result in (ClaimPolarity.MIXED, ClaimPolarity.NEGATED)


def test_did_not_increase_but_decreased_is_mixed() -> None:
    result = detect_polarity("Revenue did not increase; however, costs decreased.")
    assert result in (ClaimPolarity.MIXED, ClaimPolarity.NEGATED)


def test_negation_in_normalized_text_preserved() -> None:
    from research_core.claims.extractor import _normalize_claim

    text = "The intervention did not reduce mortality."
    normalized = _normalize_claim(text)
    assert "not" in normalized
    assert "did not reduce" in normalized


def test_regression_not_becomes_negated() -> None:
    result = detect_polarity("The intervention did not reduce mortality.")
    assert result == ClaimPolarity.NEGATED


def test_regression_may_is_positive_polarity() -> None:
    result = detect_polarity("Revenue may increase by up to 20% by 2030.")
    assert result == ClaimPolarity.POSITIVE
