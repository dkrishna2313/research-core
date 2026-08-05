"""
Sentence segmentation, clause segmentation, and assertiveness detection.

All functions are deterministic: same input → same output. No randomness,
no network access, no optional dependencies.

Sentence segmentation is English-oriented. It handles common abbreviations,
decimal numbers, initials, bullets, CRLF, and Unicode punctuation, but does
not claim full linguistic coverage.

Clause segmentation is conservative: it only splits on semicolons and the
coordinating conjunction "but" where both halves form plausible assertions.
"""

from __future__ import annotations

import re

from research_core.claims.contracts import RejectionReason

# ---------------------------------------------------------------------------
# Abbreviations that suppress sentence-boundary detection on a trailing period
# ---------------------------------------------------------------------------

_ABBREVIATIONS: frozenset[str] = frozenset(
    {
        "e.g",
        "i.e",
        "etc",
        "vs",
        "al",
        "fig",
        "no",
        "vol",
        "pp",
        "cf",
        "approx",
        "dept",
        "est",
        "govt",
        "corp",
        "co",
        "inc",
        "ltd",
        "llc",
        "mr",
        "mrs",
        "ms",
        "dr",
        "prof",
        "sr",
        "jr",
        "rev",
        "gen",
        "sgt",
        "u.s",
        "u.k",
        "u.s.a",
        "u.n",
        "e.u",
        "jan",
        "feb",
        "mar",
        "apr",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    }
)

# Sentence-ending punctuation patterns
_SENT_END = re.compile(
    r"""
    (?:
        (?<!\d)\.(?!\d)     # period not between digits (not a decimal)
        | [?!]              # question mark or exclamation
        | \.{3}             # ellipsis (three dots)
        | …            # Unicode ellipsis character
    )
    (?:\s+|$)
    """,
    re.VERBOSE,
)

# Bullet-point line starters
_BULLET_RE = re.compile(r"^[\s]*[•\-\*–—·][\s]+", re.MULTILINE)
_NUMBERED_BULLET_RE = re.compile(r"^[\s]*\d+[.):]\s+", re.MULTILINE)

# Negation patterns for polarity detection (used here for assertiveness)
_QUESTION_WORDS = frozenset(
    {"what", "when", "where", "who", "whom", "whose", "which", "why", "how"}
)

# Common boilerplate patterns
_BOILERPLATE_RE = re.compile(
    r"""
    (?:
        ^\s*©\s*\d{4}           # copyright notice
        | ^\s*copyright\s+\d{4} # copyright text
        | ^\s*all\s+rights?\s+reserved
        | ^\s*terms?\s+(?:of\s+)?(?:service|use)
        | ^\s*privacy\s+policy
        | ^\s*cookie\s+policy
        | ^\s*click\s+here
        | ^\s*read\s+more
        | ^\s*(?:skip\s+to|jump\s+to)\s+
        | ^\s*(?:home|back|next|previous|search|menu|navigation|footer|header)\s*$
        | ^\s*(?:table\s+of\s+contents|contents?)\s*$
        | ^\s*(?:share|tweet|like|follow)\s*$
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

_URL_RE = re.compile(r"^\s*https?://\S+\s*$", re.IGNORECASE)

_CITATION_RE = re.compile(r"^\s*\[\d+\]\s*(?:\S.*)?$")

# Simple imperative command starters (conservative list)
_COMMAND_STARTERS = frozenset(
    {
        "click",
        "see",
        "visit",
        "go",
        "read",
        "learn",
        "find",
        "get",
        "download",
        "subscribe",
        "sign",
        "register",
        "log",
        "contact",
        "call",
        "email",
        "send",
        "share",
        "follow",
        "like",
        "tweet",
        "print",
        "save",
        "open",
        "close",
        "select",
        "choose",
        "enter",
        "type",
        "press",
        "scroll",
    }
)

# Finite auxiliary verbs — used for assertiveness detection in full sentences
_VERB_FORMS = re.compile(
    r"""
    \b(?:
        is|are|was|were|be|been|being|
        has|have|had|
        do|does|did|
        will|would|shall|should|may|might|can|could|must|
        \w+(?:ed|s|ing)\b  # regular verb forms
    )\b
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Strictly finite auxiliary verbs — used for heading exclusion only.
# Deliberately excludes \w+s/ed/ing so nouns like "References" don't match.
_FINITE_VERB_RE = re.compile(
    r"\b(?:is|are|was|were|be|been|being|has|have|had|do|does|did|"
    r"will|would|shall|should|may|might|can|could|must)\b",
    re.IGNORECASE,
)

# Non-auxiliary assertive verbs for _has_assertion (not captured by _VERB_FORMS)
_ASSERTIVE_VERB_RE = re.compile(
    r"\b(?:increased?|decreased?|fell|fallen|rose|risen|grew|grown|"
    r"improved?|declined?|remained?|showed?|found|appear|seems?|"
    r"suggest|indicate|demonstrate|reveal|confirm|prove|show|explain|"
    r"describe|define|refer|mean|state|report|announce|estimate|project|"
    r"forecast|predict|recommend|require|prohibit|allow|permit|enable|"
    r"cause|lead|result|affect|impact|influence|drive|reduce|increase|"
    r"represent|account|constitute|comprise|exceed|reach|achieve)\b",
    re.IGNORECASE,
)


def segment_sentences(text: str) -> list[tuple[str, int, int]]:
    """Split text into sentences and return (sentence_text, start, end) triples.

    start and end are character offsets into the original text string.
    The sentence_text is text[start:end].

    Handles:
    - Standard sentence-ending punctuation (.?!)
    - Common English abbreviations (Dr., e.g., U.S., etc.)
    - Decimal numbers (3.5 does not split)
    - Single-letter initials (A. Smith)
    - CRLF and LF line boundaries
    - Bullet-point lines
    - Unicode ellipsis (…)
    - Empty input

    This segmenter is English-oriented and does not guarantee accuracy for
    other languages.
    """
    if not text or not text.strip():
        return []

    # Normalize CRLF to LF for consistent processing
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # First pass: split by bullet-point lines — each bullet is its own sentence
    if _BULLET_RE.search(normalized) or _NUMBERED_BULLET_RE.search(normalized):
        results = _split_by_bullets(text, normalized)
        if results:
            return results

    # Second pass: rule-based sentence boundary detection
    return _split_by_punctuation(text, normalized)


def _split_by_bullets(original: str, normalized: str) -> list[tuple[str, int, int]]:
    """Split text on bullet-point line boundaries."""
    lines = normalized.split("\n")
    results: list[tuple[str, int, int]] = []
    orig_pos = 0

    for line in lines:
        stripped = line.strip()
        # Strip leading bullet marker
        content = re.sub(r"^[•\-\*–—·\d][.):]*\s*", "", stripped)
        if not content:
            # Advance position past this line
            line_len = len(line) + 1  # +1 for \n
            orig_pos += _advance_normalized_to_original(original, orig_pos, line_len)
            continue

        # Find this content in the original
        start_in_orig = original.find(content[:20], orig_pos) if content else -1
        if start_in_orig == -1:
            # Fallback: just advance by line length
            orig_pos += len(line) + 1
            continue

        end_in_orig = start_in_orig + len(content)
        # Clamp to original bounds
        end_in_orig = min(end_in_orig, len(original))
        if start_in_orig < end_in_orig:
            results.append((original[start_in_orig:end_in_orig], start_in_orig, end_in_orig))
        orig_pos = end_in_orig

    if not results:
        return []
    return results


def _advance_normalized_to_original(original: str, pos: int, n: int) -> int:
    """Advance pos by approximately n characters, accounting for CRLF expansion."""
    return min(n, len(original) - pos)


def _split_by_punctuation(original: str, normalized: str) -> list[tuple[str, int, int]]:
    """Split text into sentences using punctuation-based rules."""
    # Work on the normalized (LF-only) version for boundary detection,
    # then map back to original offsets.
    # Since we've only replaced \r\n with \n and \r with \n, positions in
    # the normalized string may differ from the original. We handle this by
    # working on the original text directly.

    # Strategy: find candidate split points in the original text
    results: list[tuple[str, int, int]] = []
    start = 0
    i = 0
    orig = original

    while i < len(orig):
        ch = orig[i]

        # Check for sentence-ending characters
        if ch in ".?!…":
            # Ellipsis handling
            if ch == "." and i + 2 < len(orig) and orig[i + 1] == "." and orig[i + 2] == ".":
                # Three-dot ellipsis — don't split, skip all three
                i += 3
                continue

            if ch == ".":
                if _is_decimal_dot(orig, i):
                    i += 1
                    continue
                if _is_abbreviation_dot(orig, i):
                    i += 1
                    continue
                if _is_initial_dot(orig, i):
                    i += 1
                    continue

            # Check what follows the punctuation
            j = i + 1
            # Skip any closing quotes/parens
            while j < len(orig) and orig[j] in ')"\'»”':
                j += 1
            # Skip whitespace
            k = j
            while k < len(orig) and orig[k] in " \t\n\r":
                k += 1

            if k >= len(orig):
                # End of text — close final sentence
                sent = orig[start:].strip()
                if sent:
                    sent_start = orig.find(sent[0], start)
                    results.append((sent, sent_start, sent_start + len(sent)))
                i += 1
                start = i
                break

            # Split if followed by uppercase or a new paragraph
            next_ch = orig[k]
            if next_ch.isupper() or orig[j:k].count("\n") >= 1:
                sent = orig[start : i + 1].strip()
                if sent:
                    sent_start = _find_stripped_start(orig, start, sent)
                    results.append((sent, sent_start, sent_start + len(sent)))
                start = k
                i = k
                continue

        # Check for double newlines (paragraph boundary)
        if ch == "\n" and i + 1 < len(orig) and orig[i + 1] == "\n":
            sent = orig[start:i].strip()
            if sent:
                sent_start = _find_stripped_start(orig, start, sent)
                results.append((sent, sent_start, sent_start + len(sent)))
            start = i + 2
            i = i + 2
            continue

        i += 1

    # Remaining text after last boundary
    remaining = orig[start:].strip()
    if remaining:
        rem_start = _find_stripped_start(orig, start, remaining)
        results.append((remaining, rem_start, rem_start + len(remaining)))

    # Filter empty results
    return [(t, s, e) for t, s, e in results if t.strip()]


def _find_stripped_start(text: str, from_pos: int, stripped: str) -> int:
    """Find the start position of stripped text within text[from_pos:]."""
    if not stripped:
        return from_pos
    idx = text.find(stripped[0], from_pos)
    if idx == -1:
        return from_pos
    return idx


def _is_decimal_dot(text: str, i: int) -> bool:
    """Return True if the dot at position i is inside a decimal number."""
    if i > 0 and i + 1 < len(text):
        return text[i - 1].isdigit() and text[i + 1].isdigit()
    return False


def _is_abbreviation_dot(text: str, i: int) -> bool:
    """Return True if the dot at position i ends a known abbreviation."""
    # Extract the word before the dot (lowercase)
    j = i - 1
    while j >= 0 and (text[j].isalpha() or text[j] == "."):
        j -= 1
    word = text[j + 1 : i].lower().rstrip(".")
    if word in _ABBREVIATIONS:
        return True
    # Also check for patterns like "U.S." or "U.K."
    # Detect sequences of single letters separated by dots: A.B.C
    segment = text[j + 1 : i + 1]
    return bool(re.match(r"^(?:[A-Za-z]\.)+$", segment))


def _is_initial_dot(text: str, i: int) -> bool:
    """Return True if dot follows a single capital letter (initial in a name)."""
    if i == 0:
        return False
    if not text[i - 1].isupper():
        return False
    # Check that the character before that is a space or start
    if i >= 2 and text[i - 2] not in (" ", "\t", "\n", "("):
        return False
    # Check that what follows is a space then an uppercase letter (a name follows)
    j = i + 1
    while j < len(text) and text[j] == " ":
        j += 1
    return bool(j < len(text) and text[j].isupper())


# ---------------------------------------------------------------------------
# Clause segmentation
# ---------------------------------------------------------------------------

_SEMICOLON_RE = re.compile(r";")
_BUT_RE = re.compile(r"\bbut\b", re.IGNORECASE)


def segment_clauses(
    sentence: str,
    start_offset: int,
    min_clause_chars: int = 8,
) -> list[tuple[str, int, int]]:
    """Split a sentence into clause candidates.

    Returns list of (text, abs_start, abs_end) where offsets are absolute
    positions within the original evidence content string (start_offset +
    relative position within sentence).

    Conservative rules:
    - Split on semicolons only when both halves are >= min_clause_chars.
    - Split on " but " only when both halves are >= min_clause_chars.
    - Do NOT split on plain "and", "or", commas, or em dashes.
    - Preserve numeric ranges (between X and Y).

    Returns the original sentence as a single clause when no valid split found.
    """
    if not sentence:
        return []

    candidates = _try_semicolon_split(sentence, start_offset, min_clause_chars)
    if len(candidates) > 1:
        return candidates

    candidates = _try_but_split(sentence, start_offset, min_clause_chars)
    if len(candidates) > 1:
        return candidates

    return [(sentence, start_offset, start_offset + len(sentence))]


def _try_semicolon_split(
    text: str, start_offset: int, min_chars: int
) -> list[tuple[str, int, int]]:
    """Attempt to split on semicolons."""
    parts = _SEMICOLON_RE.split(text)
    if len(parts) <= 1:
        return [(text, start_offset, start_offset + len(text))]

    results: list[tuple[str, int, int]] = []
    pos = 0
    for part in parts:
        stripped = part.strip()
        if len(stripped) < min_chars:
            # Too short — append to previous if any, else skip
            if results:
                prev_text, prev_start, _ = results[-1]
                combined = prev_text + "; " + stripped
                results[-1] = (combined, prev_start, prev_start + len(combined))
            pos += len(part) + 1
            continue
        abs_start = start_offset + text.find(stripped, pos)
        abs_end = abs_start + len(stripped)
        results.append((stripped, abs_start, abs_end))
        pos += len(part) + 1

    return results if len(results) > 1 else [(text, start_offset, start_offset + len(text))]


def _try_but_split(
    text: str, start_offset: int, min_chars: int
) -> list[tuple[str, int, int]]:
    """Attempt to split on ' but ' coordinating conjunction."""
    # Find all " but " positions, skip if inside numeric ranges or quotes
    matches = list(_BUT_RE.finditer(text))
    for m in matches:
        # Check " but " has space on both sides (word boundary already ensured by \b)
        left = text[: m.start()].strip()
        right = text[m.end() :].strip()
        if len(left) >= min_chars and len(right) >= min_chars:
            left_start = start_offset + text.index(left[0]) if left else start_offset
            left_start = start_offset + (text.find(left, 0) if left else 0)
            right_start = start_offset + text.find(right, m.end()) if right else start_offset
            return [
                (left, left_start, left_start + len(left)),
                (right, right_start, right_start + len(right)),
            ]
    return [(text, start_offset, start_offset + len(text))]


# ---------------------------------------------------------------------------
# Assertiveness detection
# ---------------------------------------------------------------------------


def is_assertive(text: str, min_chars: int = 10) -> tuple[bool, RejectionReason | None]:
    """Return (is_assertive, rejection_reason) for a candidate text.

    Conservative: err on the side of accepting candidates.
    Only rejects when clearly non-assertive.
    """
    stripped = text.strip()

    if not stripped:
        return False, RejectionReason.EMPTY

    # Check heading before length — short common headings ("Overview") should be caught
    if _looks_like_heading(stripped):
        return False, RejectionReason.HEADING

    if len(stripped) < min_chars:
        return False, RejectionReason.TOO_SHORT

    # URL-only
    if _URL_RE.match(stripped):
        return False, RejectionReason.FRAGMENT

    # Copyright / boilerplate
    if _BOILERPLATE_RE.match(stripped):
        return False, RejectionReason.BOILERPLATE

    # Citation-only: [1] or [1, 2, 3]
    if _CITATION_RE.match(stripped) and len(stripped) < 20:
        return False, RejectionReason.CITATION_ONLY

    # Question: starts with question word and ends with ?
    words = stripped.lower().split()
    if stripped.endswith("?") and words and words[0] in _QUESTION_WORDS:
        return False, RejectionReason.QUESTION

    # Command: starts with known imperative verb
    if (
        words
        and words[0] in _COMMAND_STARTERS
        and len(stripped) < 40
        and not _VERB_FORMS.search(stripped[len(words[0]) :])
    ):
        return False, RejectionReason.COMMAND

    # Fragment: no verb-like word detected and no number
    if not _has_assertion(stripped):
        return False, RejectionReason.NO_ASSERTION

    return True, None


def _looks_like_heading(text: str) -> bool:
    """Heuristic: return True if text looks like a section heading."""
    stripped = text.strip().rstrip(":")
    # Longer than 60 chars — unlikely to be a bare heading
    if len(stripped) > 60:
        return False
    # Must not contain sentence-ending punctuation (except colon at end)
    if re.search(r"[.!?]", stripped):
        return False
    # Must not contain a number (headings with numbers are sometimes assertions)
    if re.search(r"\d", stripped):
        return False
    # Must not have a finite auxiliary verb — use _FINITE_VERB_RE, not _VERB_FORMS,
    # to avoid matching nouns that end in 's' (e.g. "References", "Results")
    if _FINITE_VERB_RE.search(stripped):
        return False
    # Must have at least one word of length >= 3 to be a recognizable heading.
    # This prevents tiny strings like "Hi" from matching (they should get TOO_SHORT).
    words = stripped.split()
    if not words:
        return False
    if not any(len(w) >= 3 for w in words):
        return False
    # More than 8 words — probably a sentence, not a heading
    return not len(words) > 8


def _has_assertion(text: str) -> bool:
    """Return True if the text contains verb-like or numeric content."""
    if re.search(r"\d", text):
        return True
    if _VERB_FORMS.search(text):
        return True
    # Check for common assertive patterns without listed verbs
    return bool(_ASSERTIVE_VERB_RE.search(text))
