"""Tests for temporal expression extraction."""

from __future__ import annotations

import pytest

from research_core.claims._classify import extract_temporal
from research_core.claims.contracts import TemporalKind

pytestmark = pytest.mark.claims


def test_plain_year_extracted() -> None:
    exprs = extract_temporal("In 2025, costs rose.")
    years = [e for e in exprs if e.kind == TemporalKind.YEAR and e.text == "2025"]
    assert len(years) >= 1


def test_year_range_extracted() -> None:
    exprs = extract_temporal("Between 2024 and 2030.")
    ranges = [e for e in exprs if e.kind == TemporalKind.RANGE]
    assert len(ranges) >= 1
    assert "2024" in ranges[0].text


def test_month_date_extracted() -> None:
    exprs = extract_temporal("January 5, 2026 was a key date.")
    dates = [e for e in exprs if e.kind == TemporalKind.DATE]
    assert len(dates) >= 1
    assert "January" in dates[0].text


def test_deadline_extracted() -> None:
    exprs = extract_temporal("By 2030, emissions will fall.")
    deadlines = [e for e in exprs if e.kind == TemporalKind.DEADLINE]
    assert len(deadlines) >= 1
    assert "2030" in deadlines[0].text


def test_duration_within_years() -> None:
    exprs = extract_temporal("Within three years.")
    durations = [e for e in exprs if e.kind == TemporalKind.DURATION]
    assert len(durations) >= 1


def test_relative_next_quarter() -> None:
    exprs = extract_temporal("Next quarter results will be published.")
    rel = [e for e in exprs if e.kind == TemporalKind.RELATIVE]
    assert len(rel) >= 1


def test_relative_not_resolved() -> None:
    # Relative expressions must NOT be resolved to absolute dates
    exprs = extract_temporal("Next quarter the results will be published.")
    rel = [e for e in exprs if e.kind == TemporalKind.RELATIVE]
    assert len(rel) >= 1
    assert "next quarter" in rel[0].text.lower()


def test_offsets_correct() -> None:
    text = "In 2025, costs rose significantly."
    exprs = extract_temporal(text)
    for expr in exprs:
        assert text[expr.start_char : expr.end_char] == expr.text


def test_sorted_by_start_char() -> None:
    text = "Between 2020 and 2030, by 2035 the deadline."
    exprs = extract_temporal(text)
    starts = [e.start_char for e in exprs]
    assert starts == sorted(starts)


def test_no_year_in_url() -> None:
    exprs = extract_temporal("See https://example.com/page/2024/report for details.")
    years_2024 = [e for e in exprs if e.text == "2024"]
    assert len(years_2024) == 0


def test_iso_date_extracted() -> None:
    exprs = extract_temporal("The date was 2026-01-05.")
    dates = [e for e in exprs if e.kind == TemporalKind.DATE]
    assert len(dates) >= 1
