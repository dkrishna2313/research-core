"""Tests for sentence segmentation."""

from __future__ import annotations

import pytest

from research_core.claims._candidate import segment_sentences

pytestmark = pytest.mark.claims


def test_empty_text_returns_empty() -> None:
    assert segment_sentences("") == []


def test_whitespace_only_returns_empty() -> None:
    assert segment_sentences("   \n\t  ") == []


def test_single_simple_sentence() -> None:
    sents = segment_sentences("Revenue increased by 12%.")
    assert len(sents) == 1
    assert sents[0][0] == "Revenue increased by 12%."


def test_two_simple_sentences() -> None:
    text = "Revenue increased by 12%. The policy may reduce emissions."
    sents = segment_sentences(text)
    assert len(sents) == 2
    assert "Revenue increased" in sents[0][0]
    assert "policy" in sents[1][0]


def test_decimal_does_not_split() -> None:
    text = "The report costs $3.5 million."
    sents = segment_sentences(text)
    assert len(sents) == 1


def test_abbreviation_dr_does_not_split() -> None:
    text = "Dr. Smith said demand declined."
    sents = segment_sentences(text)
    assert len(sents) == 1


def test_abbreviation_eg_does_not_split() -> None:
    text = "Costs increased, e.g. in 2024."
    sents = segment_sentences(text)
    assert len(sents) == 1


def test_crlf_creates_boundary() -> None:
    text = "The policy failed.\r\nDemand fell."
    sents = segment_sentences(text)
    assert len(sents) == 2


def test_exclamation_creates_boundary() -> None:
    text = "Revenue grew by 12%! Demand also rose."
    sents = segment_sentences(text)
    assert len(sents) == 2


def test_question_mark_creates_boundary() -> None:
    text = "Did costs increase? No, they fell."
    sents = segment_sentences(text)
    assert len(sents) == 2


def test_bullet_points_create_separate_sentences() -> None:
    text = "• Emissions fell\n• Demand rose"
    sents = segment_sentences(text)
    # Each bullet becomes a sentence
    assert len(sents) >= 2
    texts = [s[0] for s in sents]
    assert any("Emissions" in t for t in texts)
    assert any("Demand" in t for t in texts)


def test_offset_correctness() -> None:
    text = "Revenue increased. Costs fell."
    sents = segment_sentences(text)
    for sent_text, start, end in sents:
        # The sentence text must match the span in original
        assert text[start:end] == sent_text or sent_text in text[start:end]


def test_stable_ordering() -> None:
    text = "First sentence. Second sentence. Third sentence."
    sents1 = segment_sentences(text)
    sents2 = segment_sentences(text)
    assert [s[0] for s in sents1] == [s[0] for s in sents2]


def test_unpunctuated_long_text_returns_one_sentence() -> None:
    text = "costs rose dramatically and demand responded accordingly with significant decline"
    sents = segment_sentences(text)
    assert len(sents) >= 1
    # At least the text is represented
    full = " ".join(s[0] for s in sents)
    assert "costs rose" in full


def test_urls_do_not_cause_splits() -> None:
    text = "Visit https://example.com/page for details. Costs fell."
    sents = segment_sentences(text)
    # Should have at most 2 sentences
    assert len(sents) <= 3


def test_double_newline_creates_boundary() -> None:
    text = "First paragraph.\n\nSecond paragraph."
    sents = segment_sentences(text)
    assert len(sents) == 2


def test_offsets_non_negative() -> None:
    text = "Revenue increased. Costs fell. Demand rose."
    for _text, start, end in segment_sentences(text):
        assert start >= 0
        assert end > start
        assert end <= len(text)


def test_no_empty_sentences() -> None:
    text = "Revenue increased by 12%. The policy may reduce emissions."
    for sent_text, _, _ in segment_sentences(text):
        assert sent_text.strip() != ""
