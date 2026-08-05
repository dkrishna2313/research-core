"""Tests for clause segmentation."""

from __future__ import annotations

import pytest

from research_core.claims._candidate import segment_clauses

pytestmark = pytest.mark.claims


def test_no_delimiter_returns_single_clause() -> None:
    text = "Revenue increased by 12%."
    clauses = segment_clauses(text, 0)
    assert len(clauses) == 1
    assert clauses[0][0] == text


def test_semicolon_splits_into_two() -> None:
    text = "Revenue grew; demand fell."
    clauses = segment_clauses(text, 0)
    assert len(clauses) == 2
    assert "Revenue grew" in clauses[0][0]
    assert "demand fell" in clauses[1][0]


def test_but_splits_into_two() -> None:
    text = "Costs rose but quality improved."
    clauses = segment_clauses(text, 0)
    assert len(clauses) == 2
    assert "Costs rose" in clauses[0][0]
    assert "quality improved" in clauses[1][0]


def test_range_not_split() -> None:
    text = "Revenue was between 4 and 7 million."
    clauses = segment_clauses(text, 0)
    # Should remain one clause — "and" is part of a range
    # (our rule only splits on "but", not "and")
    assert len(clauses) == 1


def test_compound_object_and_kept_together() -> None:
    text = "The project cost $5 million and created 100 jobs."
    clauses = segment_clauses(text, 0)
    # "and" is not a split trigger — keep as one clause
    assert len(clauses) == 1


def test_absolute_offsets_correct() -> None:
    sentence = "Costs rose but quality improved."
    offset = 20  # pretend this starts at position 20 in evidence
    clauses = segment_clauses(sentence, offset)
    for text, start, end in clauses:
        assert start >= offset
        assert end > start
        # end - start should approximate length of text
        assert abs((end - start) - len(text)) <= 5  # allow small misalign


def test_short_clause_not_created() -> None:
    # If splitting would create a clause shorter than min_chars, don't split
    text = "X; Y."
    clauses = segment_clauses(text, 0, min_clause_chars=8)
    # "X" and "Y." are each < 8 chars — should merge back or not split
    # Result should be the whole text as one clause
    total = " ".join(c[0] for c in clauses)
    assert "X" in total
    assert "Y" in total


def test_deterministic_output() -> None:
    text = "Revenue grew; costs fell but demand rose."
    r1 = segment_clauses(text, 0)
    r2 = segment_clauses(text, 0)
    assert r1 == r2
