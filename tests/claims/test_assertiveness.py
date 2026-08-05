"""Tests for assertiveness detection."""

from __future__ import annotations

import pytest

from research_core.claims._candidate import is_assertive
from research_core.claims.contracts import RejectionReason

pytestmark = pytest.mark.claims


# Assertive candidates
@pytest.mark.parametrize(
    "text",
    [
        "Revenue increased by 12%.",
        "The policy may reduce emissions.",
        "Resilience means the ability to recover.",
        "Higher prices led to lower demand.",
        "The agency said costs would rise.",
        "Companies should disclose material risks.",
        "Emissions fell by 15% between 2020 and 2024.",
        "The intervention did not reduce mortality rates.",
        "According to the report, costs increased.",
        "The project will cost $5 million.",
    ],
)
def test_accepted_assertions(text: str) -> None:
    result, reason = is_assertive(text)
    assert result is True, f"Expected assertive but got rejected ({reason}): {text!r}"


# Rejections
def test_empty_text_rejected() -> None:
    result, reason = is_assertive("")
    assert result is False
    assert reason == RejectionReason.EMPTY


def test_whitespace_only_rejected() -> None:
    result, reason = is_assertive("   ")
    assert result is False
    assert reason == RejectionReason.EMPTY


def test_too_short_rejected() -> None:
    result, reason = is_assertive("Hi", min_chars=10)
    assert result is False
    assert reason == RejectionReason.TOO_SHORT


def test_question_rejected() -> None:
    result, reason = is_assertive("What caused the increase?")
    assert result is False
    assert reason == RejectionReason.QUESTION


def test_heading_overview_rejected() -> None:
    result, reason = is_assertive("Overview")
    assert result is False
    assert reason == RejectionReason.HEADING


def test_heading_references_rejected() -> None:
    result, reason = is_assertive("References")
    assert result is False
    assert reason == RejectionReason.HEADING


def test_url_only_rejected() -> None:
    result, reason = is_assertive("https://example.com")
    assert result is False
    assert reason == RejectionReason.FRAGMENT


def test_copyright_rejected() -> None:
    result, reason = is_assertive("© 2026 Example Corp.")
    assert result is False
    assert reason == RejectionReason.BOILERPLATE


def test_click_here_rejected() -> None:
    result, reason = is_assertive("Click here")
    assert result is False


def test_figure_label_rejected() -> None:
    result, reason = is_assertive("Figure 3")
    # Could be heading or fragment — either is acceptable
    assert result is False
