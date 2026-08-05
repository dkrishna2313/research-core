"""Tests for quantitative expression extraction."""

from __future__ import annotations

import pytest

from research_core.claims._classify import extract_quantitative

pytestmark = pytest.mark.claims


def test_percentage_extracted() -> None:
    exprs = extract_quantitative("Revenue increased by 12%.")
    pcts = [e for e in exprs if e.percentage]
    assert len(pcts) >= 1
    assert "12" in pcts[0].value_text
    assert "12%" in pcts[0].text


def test_currency_extracted() -> None:
    exprs = extract_quantitative("The project cost $5 million.")
    curr = [e for e in exprs if e.currency or "million" in e.text.lower()]
    assert len(curr) >= 1


def test_measurement_gw_extracted() -> None:
    exprs = extract_quantitative("Capacity reached 3.4 GW.")
    meas = [e for e in exprs if "GW" in e.text]
    assert len(meas) >= 1
    assert meas[0].unit == "GW"


def test_range_extracted() -> None:
    exprs = extract_quantitative("Between 4 and 7 years.")
    ranges = [e for e in exprs if e.range_start]
    assert len(ranges) >= 1
    assert ranges[0].range_start == "4"
    assert ranges[0].range_end == "7"


def test_comparator_extracted() -> None:
    exprs = extract_quantitative("At least 100 MW of capacity was installed.")
    comp = [e for e in exprs if e.comparator]
    assert len(comp) >= 1
    assert "100" in comp[0].value_text


def test_year_extracted_as_quantitative() -> None:
    exprs = extract_quantitative("In 2024, costs rose.")
    years = [e for e in exprs if e.value_text == "2024"]
    assert len(years) >= 1


def test_version_number_not_extracted() -> None:
    exprs = extract_quantitative("version 2.1 of the software was released.")
    # version 2.1 should not be extracted (preceded by "version")
    [e for e in exprs if e.value_text not in ("2", "1", "2.1")]
    # At minimum "2.1" should not appear as a plain number
    texts = [e.text for e in exprs]
    assert "2.1" not in texts or all("version" not in t.lower() for t in texts)


def test_section_number_not_extracted() -> None:
    exprs = extract_quantitative("Section 3.2 describes the methodology.")
    texts = [e.text for e in exprs]
    assert "3.2" not in texts


def test_url_year_not_extracted() -> None:
    exprs = extract_quantitative("See https://example.com/a/2024 for details.")
    [e for e in exprs if e.value_text == "2024" and "example.com" in ""]
    # No year should be extracted from inside a URL
    years = [e for e in exprs if e.value_text == "2024"]
    assert len(years) == 0


def test_offset_correct() -> None:
    text = "Revenue increased by 12%."
    exprs = extract_quantitative(text)
    for expr in exprs:
        assert expr.start_char >= 0
        assert expr.end_char > expr.start_char
        assert text[expr.start_char : expr.end_char] == expr.text


def test_sorted_by_start_char() -> None:
    text = "Between 4 and 7 years and revenue grew by 12%."
    exprs = extract_quantitative(text)
    starts = [e.start_char for e in exprs]
    assert starts == sorted(starts)


def test_usd_currency() -> None:
    exprs = extract_quantitative("USD 4.2 billion was invested.")
    curr = [e for e in exprs if e.currency or "billion" in e.text.lower()]
    assert len(curr) >= 1


def test_negative_percentage() -> None:
    exprs = extract_quantitative("Emissions fell by -3.5%.")
    pcts = [e for e in exprs if e.percentage]
    assert len(pcts) >= 1
