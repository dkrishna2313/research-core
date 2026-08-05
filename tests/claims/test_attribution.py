"""Tests for attribution extraction."""

from __future__ import annotations

import pytest

from research_core.claims._classify import extract_attribution

pytestmark = pytest.mark.claims


def test_according_to_pattern() -> None:
    attr = extract_attribution("According to the report, costs increased.")
    assert attr is not None
    assert "report" in attr.source_text
    assert "according to" in attr.reporting_verb.lower()
    assert "costs increased" in attr.attributed_text


def test_said_pattern() -> None:
    attr = extract_attribution("The agency said demand declined.")
    assert attr is not None
    assert "agency" in attr.source_text.lower()
    assert "said" in attr.reporting_verb.lower()
    assert "demand declined" in attr.attributed_text


def test_estimates_pattern() -> None:
    attr = extract_attribution("Researchers estimate the market may grow.")
    assert attr is not None
    assert "Researchers" in attr.source_text
    assert "estimate" in attr.reporting_verb.lower()


def test_announced_pattern() -> None:
    attr = extract_attribution("The company announced that production stopped.")
    assert attr is not None
    assert "company" in attr.source_text.lower()
    assert "announced" in attr.reporting_verb.lower()


def test_no_attribution_returns_none() -> None:
    attr = extract_attribution("Revenue increased by 12%.")
    assert attr is None


def test_no_attribution_negated() -> None:
    attr = extract_attribution("The intervention did not reduce mortality rates.")
    assert attr is None


def test_attribution_offsets_valid() -> None:
    text = "According to the agency, costs increased by $2 million."
    attr = extract_attribution(text)
    assert attr is not None
    assert attr.start_char >= 0
    assert attr.end_char > attr.start_char
