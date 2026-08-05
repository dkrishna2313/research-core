"""
Claim classification, modality detection, polarity detection,
quantitative extraction, temporal extraction, and attribution extraction.

All functions are deterministic and rely only on the Python standard library.
No LLM, no NLP library, no network access.

Classification precedence:
  NORMATIVE > PREDICTIVE > CAUSAL > COMPARATIVE > QUANTITATIVE >
  DEFINITIONAL > FACTUAL > UNKNOWN

When multiple signals are present in a single sentence, the first matching
category in the precedence order is used.
"""

from __future__ import annotations

import re

from research_core.claims.contracts import (
    ClaimAttribution,
    ClaimModality,
    ClaimPolarity,
    ClaimQualifier,
    ClaimQualifierKind,
    ClaimType,
    QuantitativeExpression,
    TemporalExpression,
    TemporalKind,
)

# ---------------------------------------------------------------------------
# Classification patterns
# ---------------------------------------------------------------------------

_NORMATIVE_RE = re.compile(
    r"\b(?:should|must|ought\s+to|needs?\s+to|required?\s+to|recommended?|"
    r"obligat(?:ed?|ion)|mandated?|necessary|imperative|essential\s+that)\b",
    re.IGNORECASE,
)

_PREDICTIVE_RE = re.compile(
    r"\b(?:will|is\s+expected\s+to|are\s+expected\s+to|is\s+projected\s+to|"
    r"are\s+projected\s+to|forecast(?:ed?)?|is\s+predicted|predicted\s+to|"
    r"would|shall|is\s+anticipated|are\s+anticipated|expects?\s+to|"
    r"projected?\s+to|anticipated?\s+to|set\s+to)\b",
    re.IGNORECASE,
)

_CAUSAL_RE = re.compile(
    r"\b(?:because|caused?|led\s+to|results?\s+in|resulted\s+in|resulting\s+in|"
    r"due\s+to|therefore|consequently|hence|thus|so\s+that|drives?|driven\s+by|"
    r"enables?|enabled\s+by|reduces?|increases?|leads?\s+to|trigger(?:ed|s)?|"
    r"stems?\s+from|attributed?\s+to|owing\s+to|as\s+a\s+result|"
    r"in\s+response\s+to|contributes?\s+to|generates?)\b",
    re.IGNORECASE,
)

_COMPARATIVE_RE = re.compile(
    r"\b(?:more\s+than|less\s+than|higher\s+than|lower\s+than|"
    r"greater\s+than|fewer\s+than|compared\s+(?:with|to)|versus|vs\.?|"
    r"faster\s+than|slower\s+than|larger\s+than|smaller\s+than|"
    r"larger|smaller|fastest|slowest|largest|smallest|"
    r"greater|fewer|above|below|outpac(?:ed?|ing)|exceed(?:ed?|s|ing)|"
    r"surpass(?:ed?|es|ing)|lower|higher|better\s+than|worse\s+than)\b",
    re.IGNORECASE,
)

_DEFINITIONAL_RE = re.compile(
    r"\b(?:is\s+defined\s+as|refers?\s+to|means?|is\s+called|is\s+known\s+as|"
    r"defined?\s+as|describes?\s+as|constitutes?|is\s+a\s+(?:type|form|kind|"
    r"measure|measure|concept|term)|characterized\s+by)\b",
    re.IGNORECASE,
)


def classify_claim(text: str, quant_exprs: list[QuantitativeExpression]) -> ClaimType:
    """Classify a claim using deterministic lexical rules.

    Precedence: NORMATIVE > PREDICTIVE > CAUSAL > COMPARATIVE >
                QUANTITATIVE > DEFINITIONAL > FACTUAL > UNKNOWN
    """
    if _NORMATIVE_RE.search(text):
        return ClaimType.NORMATIVE
    if _PREDICTIVE_RE.search(text):
        return ClaimType.PREDICTIVE
    if _CAUSAL_RE.search(text):
        return ClaimType.CAUSAL
    if _COMPARATIVE_RE.search(text):
        return ClaimType.COMPARATIVE
    # QUANTITATIVE: only when non-trivial numeric content is present
    # (years alone don't trigger quantitative; actual numbers/percentages/currencies do)
    if _has_nontrivial_quant(quant_exprs):
        return ClaimType.QUANTITATIVE
    if _DEFINITIONAL_RE.search(text):
        return ClaimType.DEFINITIONAL
    # FACTUAL is the default for clear assertions
    return ClaimType.FACTUAL


def _has_nontrivial_quant(exprs: list[QuantitativeExpression]) -> bool:
    """Return True if any expression is non-trivial (not just a bare year)."""
    for expr in exprs:
        if expr.percentage:
            return True
        if expr.currency:
            return True
        if expr.unit:
            return True
        if expr.comparator:
            return True
        if expr.range_start:
            return True
        # A bare numeric value that is not a standalone 4-digit year
        if expr.value_text and not re.match(r"^(19|20)\d{2}$", expr.value_text.strip()):
            return True
    return False


# ---------------------------------------------------------------------------
# Modality detection
# ---------------------------------------------------------------------------

_MODALITY_RULES: list[tuple[re.Pattern[str], ClaimModality, ClaimQualifierKind]] = [
    (
        re.compile(
            r"\b(if|unless|provided\s+that|subject\s+to|assuming|given\s+that|"
            r"in\s+the\s+event\s+(?:that)?|contingent\s+(?:on|upon))\b",
            re.IGNORECASE,
        ),
        ClaimModality.CONDITIONAL,
        ClaimQualifierKind.CONDITIONAL,
    ),
    (
        re.compile(
            r"\b(must|shall|required?\s+to|is\s+required|are\s+required|"
            r"obligated?\s+to|mandated?|compelled?\s+to)\b",
            re.IGNORECASE,
        ),
        ClaimModality.REQUIRED,
        ClaimQualifierKind.MODAL,
    ),
    (
        re.compile(
            r"\b(should|ought\s+to|recommended?|advisable|suggested?\s+that)\b",
            re.IGNORECASE,
        ),
        ClaimModality.RECOMMENDED,
        ClaimQualifierKind.MODAL,
    ),
    (
        re.compile(
            r"\b(likely|probably|expected?\s+to|is\s+expected|are\s+expected|"
            r"projected?\s+to|is\s+projected|are\s+projected|anticipated?\s+to)\b",
            re.IGNORECASE,
        ),
        ClaimModality.PROBABLE,
        ClaimQualifierKind.MODAL,
    ),
    (
        re.compile(
            r"\b(may|might|could|can|possible|potentially|perhaps|conceivably)\b",
            re.IGNORECASE,
        ),
        ClaimModality.POSSIBLE,
        ClaimQualifierKind.MODAL,
    ),
]


def detect_modality(text: str) -> tuple[ClaimModality, list[ClaimQualifier]]:
    """Detect modality and return (modality, list_of_modal_qualifiers).

    First matching rule wins (precedence: CONDITIONAL > REQUIRED >
    RECOMMENDED > PROBABLE > POSSIBLE > ASSERTED).

    All matching modal terms are captured as ClaimQualifier objects.
    """
    qualifiers: list[ClaimQualifier] = []

    for pattern, modality, kind in _MODALITY_RULES:
        match = pattern.search(text)
        if match:
            # Collect ALL matches of this pattern as qualifiers
            for m in pattern.finditer(text):
                qualifiers.append(
                    ClaimQualifier(
                        text=m.group(0),
                        kind=kind,
                        start_char=m.start(),
                        end_char=m.end(),
                    )
                )
            return modality, qualifiers

    return ClaimModality.ASSERTED, []


# ---------------------------------------------------------------------------
# Polarity detection
# ---------------------------------------------------------------------------

_NEGATION_RE = re.compile(
    r"\b(?:not|no|never|neither|nor|without|cannot|can't|couldn't|didn't|"
    r"doesn't|don't|won't|wouldn't|hasn't|haven't|hadn't|isn't|aren't|"
    r"wasn't|weren't|failed?\s+to|unable\s+to|unlikely\s+to|"
    r"no\s+evidence|not\s+yet|not\s+a|not\s+the|none\s+of)\b",
    re.IGNORECASE,
)

_MIXED_RE = re.compile(
    r"\b(?:not\s+only|but\s+also|however|yet|although|though|while|whereas|"
    r"despite|in\s+contrast|on\s+the\s+other\s+hand)\b",
    re.IGNORECASE,
)


def detect_polarity(text: str) -> ClaimPolarity:
    """Detect whether the claim is positive, negated, or mixed.

    Conservative:
    - MIXED only when negation AND a mixed-signal connector are both present
    - NEGATED when negation is present without mixed signals
    - POSITIVE otherwise
    """
    has_negation = bool(_NEGATION_RE.search(text))
    has_mixed = bool(_MIXED_RE.search(text))

    if has_negation and has_mixed:
        return ClaimPolarity.MIXED
    if has_negation:
        return ClaimPolarity.NEGATED
    return ClaimPolarity.POSITIVE


# ---------------------------------------------------------------------------
# Quantitative extraction
# ---------------------------------------------------------------------------

# Patterns in priority order. Each match is (full_text, value_text, extras…)
# We use a single compiled pattern per type and process left-to-right,
# marking consumed spans to avoid overlaps.

_RANGE_RE = re.compile(
    r"\b(?:between|from)\s+(\d[\d,\.]*)\s+(?:and|to)\s+(\d[\d,\.]*)"
    r"(?:\s+([A-Za-z%°²³/]+(?:\s+[A-Za-z]+)?))?",
    re.IGNORECASE,
)

_COMPARATOR_RE = re.compile(
    r"\b(more\s+than|less\s+than|at\s+least|at\s+most|greater\s+than|"
    r"fewer\s+than|approximately|about|up\s+to|over|under|no\s+more\s+than|"
    r"no\s+less\s+than|as\s+much\s+as|as\s+few\s+as)\s+"
    r"(\d[\d,\.]*)"
    r"(?:\s*([%°℃℉]|[A-Za-z][A-Za-z²³/]*(?:\s*[A-Za-z²³/]*)?))?",
    re.IGNORECASE,
)

_PERCENT_RE = re.compile(r"-?\d[\d,\.]*\s*%")

_CURRENCY_RE = re.compile(
    r"(?:\$|€|£|¥|USD|EUR|GBP|JPY|CAD|AUD)\s*\d[\d,\.]*"
    r"(?:\s*(?:million|billion|trillion|thousand|m\b|bn\b|k\b))?",
    re.IGNORECASE,
)

_MEASUREMENT_RE = re.compile(
    r"\d[\d,\.]*\s*(?:GW|MW|kW|TWh|MWh|kWh|"
    r"km²|m²|km|ha|"
    r"kg|t\b|kt\b|Mt\b|Gt\b|"
    r"°C|°F|℃|℉|"
    r"Gt|Mt|"
    r"l\b|L\b)\b",
)

_SCALE_RE = re.compile(
    r"\d[\d,\.]*\s*(?:million|billion|trillion|thousand|percent)\b",
    re.IGNORECASE,
)

# Year pattern — must NOT be inside a URL or preceded by version/section markers
_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
_URL_CONTEXT_RE = re.compile(r"https?://\S*$", re.IGNORECASE)
_VERSION_CONTEXT_RE = re.compile(
    r"(?:version|v|section|fig(?:ure)?|table|ch(?:apter)?|no\.?|#)\s*$",
    re.IGNORECASE,
)


def extract_quantitative(text: str) -> list[QuantitativeExpression]:
    """Extract quantitative expressions from claim text.

    Returns a list of QuantitativeExpression objects with offsets into the
    claim text. Processes patterns left-to-right; once a span is consumed
    it is not matched again.

    Does not extract:
    - Version numbers (preceded by "version", "v", "section", "fig")
    - Years embedded in URLs
    - Phone numbers
    """
    results: list[QuantitativeExpression] = []
    consumed: list[tuple[int, int]] = []

    def _mark(start: int, end: int) -> None:
        consumed.append((start, end))

    def _is_consumed(start: int, end: int) -> bool:
        return any(s <= start < e or s < end <= e for s, e in consumed)

    # 1. Ranges
    for m in _RANGE_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        unit = (m.group(3) or "").strip()
        results.append(
            QuantitativeExpression(
                text=m.group(0),
                value_text=m.group(1),
                unit=unit,
                range_start=m.group(1),
                range_end=m.group(2),
                start_char=m.start(),
                end_char=m.end(),
            )
        )
        _mark(m.start(), m.end())

    # 2. Comparators
    for m in _COMPARATOR_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        unit = (m.group(3) or "").strip()
        pct = unit == "%"
        results.append(
            QuantitativeExpression(
                text=m.group(0),
                value_text=m.group(2),
                unit="" if pct else unit,
                comparator=m.group(1),
                percentage=pct,
                start_char=m.start(),
                end_char=m.end(),
            )
        )
        _mark(m.start(), m.end())

    # 3. Percentages
    for m in _PERCENT_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        val = m.group(0).replace("%", "").replace(",", "").strip()
        results.append(
            QuantitativeExpression(
                text=m.group(0),
                value_text=val,
                percentage=True,
                start_char=m.start(),
                end_char=m.end(),
            )
        )
        _mark(m.start(), m.end())

    # 4. Currency
    for m in _CURRENCY_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        full = m.group(0)
        # Extract currency symbol/code
        curr_m = re.match(r"(\$|€|£|¥|USD|EUR|GBP|JPY|CAD|AUD)", full, re.IGNORECASE)
        currency = curr_m.group(1) if curr_m else ""
        val_m = re.search(r"\d[\d,\.]*", full)
        val = val_m.group(0) if val_m else full
        results.append(
            QuantitativeExpression(
                text=full,
                value_text=val,
                currency=currency,
                start_char=m.start(),
                end_char=m.end(),
            )
        )
        _mark(m.start(), m.end())

    # 5. Measurements
    for m in _MEASUREMENT_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        full = m.group(0)
        val_m = re.match(r"\d[\d,\.]*", full)
        val = val_m.group(0) if val_m else full
        unit_m = re.search(r"[A-Za-z°℃℉²³/]+$", full.strip())
        unit = unit_m.group(0) if unit_m else ""
        results.append(
            QuantitativeExpression(
                text=full,
                value_text=val,
                unit=unit,
                start_char=m.start(),
                end_char=m.end(),
            )
        )
        _mark(m.start(), m.end())

    # 6. Scale numbers (million, billion, etc.)
    for m in _SCALE_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        full = m.group(0)
        val_m = re.match(r"\d[\d,\.]*", full)
        val = val_m.group(0) if val_m else full
        unit_m = re.search(r"(?:million|billion|trillion|thousand|percent)$", full, re.IGNORECASE)
        unit = unit_m.group(0) if unit_m else ""
        pct = unit.lower() == "percent"
        results.append(
            QuantitativeExpression(
                text=full,
                value_text=val,
                unit="" if pct else unit,
                percentage=pct,
                start_char=m.start(),
                end_char=m.end(),
            )
        )
        _mark(m.start(), m.end())

    # 7. Years (as quantitative expressions — also captured as temporal)
    for m in _YEAR_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        if _has_version_prefix(text, m.start()):
            continue
        results.append(
            QuantitativeExpression(
                text=m.group(0),
                value_text=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
            )
        )
        _mark(m.start(), m.end())

    # Sort by start_char for deterministic ordering
    results.sort(key=lambda e: e.start_char)
    return results


def _in_url(text: str, pos: int) -> bool:
    """Return True if pos is inside or immediately after a URL."""
    # Check if there's a URL protocol earlier on the same line
    line_start = text.rfind("\n", 0, pos)
    if line_start == -1:
        line_start = 0
    segment = text[line_start:pos]
    return bool(re.search(r"https?://\S*$", segment, re.IGNORECASE))


def _has_version_prefix(text: str, pos: int) -> bool:
    """Return True if the word at pos is preceded by version/section markers."""
    prefix = text[:pos].rstrip()
    return bool(
        re.search(
            r"(?:version|v\.?|section|fig(?:ure)?\.?|table\.?|ch(?:apter)?\.?|no\.?|#)\s*$",
            prefix,
            re.IGNORECASE,
        )
    )


# ---------------------------------------------------------------------------
# Temporal extraction
# ---------------------------------------------------------------------------

_YEAR_RANGE_RE = re.compile(
    r"\b((?:19|20)\d{2})\s*[-–—]\s*((?:19|20)\d{2})\b"
)

_YEAR_BETWEEN_RE = re.compile(
    r"\b(?:between|from)\s+((?:19|20)\d{2})\s+(?:and|to)\s+((?:19|20)\d{2})\b",
    re.IGNORECASE,
)

_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

_MONTH_NAMES = (
    "January|February|March|April|May|June|July|August|"
    "September|October|November|December"
)
_MONTH_DATE_RE = re.compile(
    rf"\b({_MONTH_NAMES})\s+(\d{{1,2}}),?\s+(\d{{4}})\b",
    re.IGNORECASE,
)

_DECADE_RE = re.compile(r"\b((?:19|20)\d0)s\b", re.IGNORECASE)

_DEADLINE_RE = re.compile(
    rf"(?:by|before|no\s+later\s+than)\s+(?:({_MONTH_NAMES})\s+\d{{1,2}},?\s+)?((?:19|20)\d{{2}})\b",
    re.IGNORECASE,
)

_DURATION_RE = re.compile(
    r"\b(?:within|for|over|during|throughout|across)\s+"
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|fifteen|twenty|thirty)\s+"
    r"(?:year|month|week|day|decade|quarter|centur)s?\b",
    re.IGNORECASE,
)

_RELATIVE_RE = re.compile(
    r"\b(?:next|last|this|coming|recent|previous|current|past|"
    r"upcoming|the\s+following)\s+"
    r"(?:year|month|quarter|decade|week|day|period|fiscal\s+year|"
    r"calendar\s+year|half|semester)\b",
    re.IGNORECASE,
)

_PLAIN_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")


def extract_temporal(text: str) -> list[TemporalExpression]:
    """Extract temporal expressions from claim text.

    Returns a list sorted by start_char.
    Relative expressions are preserved as text — they are never resolved
    to absolute calendar dates.
    """
    results: list[TemporalExpression] = []
    consumed: list[tuple[int, int]] = []

    def _mark(start: int, end: int) -> None:
        consumed.append((start, end))

    def _is_consumed(start: int, end: int) -> bool:
        return any(s <= start < e or s < end <= e for s, e in consumed)

    # 1. Year ranges — dash/en-dash/em-dash format (2020–2030)
    for m in _YEAR_RANGE_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        results.append(
            TemporalExpression(
                text=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
                kind=TemporalKind.RANGE,
            )
        )
        _mark(m.start(), m.end())

    # 1b. Year ranges — "between/from YYYY and/to YYYY" format
    for m in _YEAR_BETWEEN_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        results.append(
            TemporalExpression(
                text=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
                kind=TemporalKind.RANGE,
            )
        )
        _mark(m.start(), m.end())

    # 2. ISO dates
    for m in _ISO_DATE_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        results.append(
            TemporalExpression(
                text=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
                kind=TemporalKind.DATE,
            )
        )
        _mark(m.start(), m.end())

    # 3. Month-name dates
    for m in _MONTH_DATE_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        results.append(
            TemporalExpression(
                text=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
                kind=TemporalKind.DATE,
            )
        )
        _mark(m.start(), m.end())

    # 4. Decades
    for m in _DECADE_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        results.append(
            TemporalExpression(
                text=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
                kind=TemporalKind.YEAR,
            )
        )
        _mark(m.start(), m.end())

    # 5. Deadlines
    for m in _DEADLINE_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        results.append(
            TemporalExpression(
                text=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
                kind=TemporalKind.DEADLINE,
            )
        )
        _mark(m.start(), m.end())

    # 6. Durations
    for m in _DURATION_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        results.append(
            TemporalExpression(
                text=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
                kind=TemporalKind.DURATION,
            )
        )
        _mark(m.start(), m.end())

    # 7. Relative expressions
    for m in _RELATIVE_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        results.append(
            TemporalExpression(
                text=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
                kind=TemporalKind.RELATIVE,
            )
        )
        _mark(m.start(), m.end())

    # 8. Plain years
    for m in _PLAIN_YEAR_RE.finditer(text):
        if _is_consumed(m.start(), m.end()):
            continue
        if _in_url(text, m.start()):
            continue
        if _has_version_prefix(text, m.start()):
            continue
        results.append(
            TemporalExpression(
                text=m.group(0),
                start_char=m.start(),
                end_char=m.end(),
                kind=TemporalKind.YEAR,
            )
        )
        _mark(m.start(), m.end())

    results.sort(key=lambda e: e.start_char)
    return results


# ---------------------------------------------------------------------------
# Attribution extraction
# ---------------------------------------------------------------------------

_ACCORDING_TO_RE = re.compile(
    r"(?:According\s+to\s+)([\w\s,\.]+?),\s+(.+)",
    re.IGNORECASE | re.DOTALL,
)

_SAID_RE = re.compile(
    r"((?:The\s+)?[\w][\w\s,\.]{1,60}?)\s+"
    r"(said|stated|reported|found|estimates?|argues?|argued|announced|"
    r"noted|claimed|concluded|showed|shows|asserts?|asserted|revealed?|"
    r"confirmed?|indicated?|highlighted?|warns?|warned|predicted?|"
    r"acknowledges?|acknowledged|suggests?|suggested)\s+"
    r"(?:that\s+)?(.+)",
    re.IGNORECASE | re.DOTALL,
)


def extract_attribution(text: str) -> ClaimAttribution | None:
    """Extract explicit attribution from claim text.

    Returns a ClaimAttribution if an explicit attribution pattern is found,
    otherwise None.

    Does not infer unstated attribution.
    Does not treat attribution as verification or corroboration.
    """
    # Pattern 1: "According to X, ..."
    m = _ACCORDING_TO_RE.match(text.strip())
    if m:
        source = m.group(1).strip().rstrip(",").strip()
        attributed = m.group(2).strip()
        if source and attributed:
            return ClaimAttribution(
                source_text=source,
                reporting_verb="according to",
                attributed_text=attributed,
                start_char=0,
                end_char=len(text.strip()),
            )

    # Pattern 2: "X said/reported/... [that] ..."
    m2 = _SAID_RE.match(text.strip())
    if m2:
        source = m2.group(1).strip()
        verb = m2.group(2).strip()
        attributed = m2.group(3).strip()
        # Sanity: source should not be too long or start with a lowercase article
        if (
            source
            and attributed
            and len(source) <= 60
            and not re.match(r"^(?:the\s+)?[a-z]", source)
        ):
            return ClaimAttribution(
                source_text=source,
                reporting_verb=verb,
                attributed_text=attributed,
                start_char=0,
                end_char=len(text.strip()),
            )

    return None
