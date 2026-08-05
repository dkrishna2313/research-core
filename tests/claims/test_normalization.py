"""Tests for claim normalization — conservative, meaning-preserving."""

from __future__ import annotations

import pytest

from research_core.claims.extractor import _normalize_claim

pytestmark = pytest.mark.claims


def test_repeated_spaces_collapsed() -> None:
    result = _normalize_claim("Revenue  increased  significantly.")
    assert "  " not in result
    assert result == "Revenue increased significantly."


def test_newline_normalized_to_space() -> None:
    result = _normalize_claim("Revenue\nincreased.")
    assert "\n" not in result
    assert result == "Revenue increased."


def test_crlf_normalized_to_space() -> None:
    result = _normalize_claim("Revenue\r\nincreased.")
    assert "\r" not in result
    assert result == "Revenue increased."


def test_surrounding_whitespace_trimmed() -> None:
    result = _normalize_claim("  Revenue increased.  ")
    assert result == "Revenue increased."


def test_unicode_nfc_applied() -> None:
    # Compose combining characters
    text = "café"  # e + combining acute = é (NFC)
    result = _normalize_claim(text)
    assert "́" not in result  # combining char merged


def test_negation_preserved() -> None:
    text = "The intervention did not reduce mortality."
    result = _normalize_claim(text)
    assert "not" in result
    assert "did not reduce" in result


def test_modal_preserved() -> None:
    text = "Revenue may increase by up to 20% by 2030."
    result = _normalize_claim(text)
    assert "may" in result


def test_percentage_preserved() -> None:
    text = "Emissions fell by 15%."
    result = _normalize_claim(text)
    assert "15%" in result


def test_currency_preserved() -> None:
    text = "The project cost $5 million."
    result = _normalize_claim(text)
    assert "$5 million" in result


def test_date_preserved() -> None:
    text = "By 2030, emissions will fall."
    result = _normalize_claim(text)
    assert "2030" in result


def test_unit_preserved() -> None:
    text = "Capacity reached 3.4 GW."
    result = _normalize_claim(text)
    assert "GW" in result


def test_condition_preserved() -> None:
    text = "If emissions fall, costs will decline."
    result = _normalize_claim(text)
    assert "If" in result


def test_attribution_preserved() -> None:
    text = "According to the agency, costs increased by $2 million."
    result = _normalize_claim(text)
    assert "According to" in result
    assert "$2 million" in result


def test_no_paraphrase() -> None:
    text = "The policy reduces carbon emissions by a significant margin."
    result = _normalize_claim(text)
    # Normalized text should not be shorter in a way that removes meaning
    assert "reduces carbon emissions" in result
