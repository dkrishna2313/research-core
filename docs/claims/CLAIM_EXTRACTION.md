# Claim Extraction — RC5

`research_core.claims` provides a deterministic, provider-neutral claim-extraction layer. It converts ranked evidence (`RankedEvidence`) into structured claims with precise evidence lineage. It performs no LLM calls, makes no network requests, and produces identical output for identical input.

---

## Package Layout

```
src/research_core/claims/
├── __init__.py          public API
├── contracts.py         all RC5 data types
├── config.py            ClaimExtractionConfig with fingerprint
├── extractor.py         ClaimExtractor protocol + DeterministicClaimExtractor
├── _candidate.py        sentence segmentation, clause splitting, assertiveness filter
├── _classify.py         claim type, modality, polarity, quantitative, temporal, attribution
└── _deduplicate.py      exact deduplication (same-parent, same-evidence, cross-source)
```

---

## Quick Start

```python
from research_core.claims import DeterministicClaimExtractor, ClaimExtractionConfig

extractor = DeterministicClaimExtractor()
result = extractor.extract(ranked_evidence_list)

for claim in result.claims:
    print(f"[{claim.claim_type}][{claim.modality}][{claim.polarity}] {claim.claim_text}")

print(f"Extracted: {result.diagnostics.claims_extracted}")
print(f"Rejected:  {result.diagnostics.claims_rejected}")
```

---

## Pipeline

```
RankedEvidence list
  → sort by rank (ascending — rank 1 is highest)
  → per evidence item:
      segment_sentences()   → (text, start, end) list
        → per sentence:
            is_assertive()    → accept or record ClaimRejection
            if accepted:
              segment_clauses()  → (text, start, end) list
                → per clause:
                    is_assertive()
                    if accepted:
                      classify_claim()
                      detect_modality()
                      detect_polarity()
                      extract_quantitative()
                      extract_temporal()
                      extract_attribution()
                      _make_claim_id()        → deterministic SHA256
                      ExtractedClaim(...)
  → deduplicate_claims()    if config.deduplicate_exact
  → build ClaimExtractionDiagnostics
  → return ClaimExtractionResult
```

---

## Sentence Segmentation

`_candidate.segment_sentences(text)` is a rule-based, English-oriented segmenter. It handles:

- Abbreviations (`Dr.`, `e.g.`, `U.S.`, `etc.`, 50+ total)
- Decimal numbers (`3.14`)
- Initials (`J. Smith`)
- CRLF and Unicode ellipsis (`…`)
- Bullet point text blocks

The function returns `list[tuple[str, int, int]]` where each entry is `(sentence_text, start_char, end_char)` with absolute offsets into the evidence content.

---

## Clause Splitting

`_candidate.segment_clauses(sentence, start_offset)` splits a sentence on semicolons and ` but ` conjunctions, returning absolute offsets. Clauses shorter than `min_clause_chars` (default 8) are discarded.

---

## Assertiveness Filter

`_candidate.is_assertive(text, min_chars)` rejects text that:

- Is empty or below `minimum_claim_characters`
- Is a question (ends with `?`)
- Is a heading (all caps or title-case fragment with no verb)
- Is a fragment without an assertion
- Is boilerplate (`Table of Contents`, `See also`, …)
- Is a bare citation (`[1]`, `(Smith et al., 2023)`)
- Is a command (starts with an imperative verb: `See`, `Note`, `Refer`, …)
- Has no assertion (no subject–verb structure)

The function returns `(bool, RejectionReason | None)`.

---

## Classification

### Claim Type

`_classify.classify_claim(text, quant_exprs)` checks types in precedence order:

| Precedence | Type | Signal |
|---|---|---|
| 1 | NORMATIVE | must, shall, should, required to, obligated to, … |
| 2 | PREDICTIVE | will, forecast, projected, expected to, by 20xx, … |
| 3 | CAUSAL | because, therefore, leads to, results in, caused by, … |
| 4 | COMPARATIVE | more than, less than, higher than, compared to, … |
| 5 | QUANTITATIVE | non-trivial numeric expression present |
| 6 | DEFINITIONAL | is defined as, refers to, consists of, … |
| 7 | FACTUAL | default for any accepted claim |
| 8 | UNKNOWN | fallback |

### Modality

`_classify.detect_modality(text)` uses first-match-wins lexical rules:

| Modality | Signal |
|---|---|
| CONDITIONAL | if …, provided that, in the event that, … |
| REQUIRED | must, shall, is required to, mandated by, … |
| RECOMMENDED | should, ought to, it is recommended that, … |
| PROBABLE | likely, probably, expected to, … |
| POSSIBLE | may, might, could, possible that, … |
| ASSERTED | default |

Modality qualifiers are captured as `ClaimQualifier` objects with `kind=MODAL` and offsets into the claim text.

### Polarity

`_classify.detect_polarity(text)` returns:

- `NEGATED` — explicit negation detected (`not`, `never`, `no`, `cannot`, …)
- `MIXED` — both negation and mixed connector (`but`, `although`, …)
- `POSITIVE` — default

Negation is never removed from `claim_text` or `normalized_text`.

---

## Quantitative and Temporal Extraction

### Quantitative

`_classify.extract_quantitative(text)` matches seven regex patterns:

1. Numeric ranges (`10–20%`, `$5m to $10m`)
2. Comparator expressions (`more than 50`)
3. Percentage values (`12%`, `12 percent`)
4. Currency amounts (`$2 million`, `€500k`)
5. Physical measurements (`50 MW`, `3.5 GW`)
6. Scale numbers (`2 million`, `1.5 billion`)
7. Year-as-number guard (bare years alone do not trigger QUANTITATIVE classification)

URL and version-string false positives are suppressed.

### Temporal

`_classify.extract_temporal(text)` matches eight patterns:

1. Year ranges (`2020–2030`)
2. ISO dates (`2024-03-15`)
3. Month-year dates (`March 2024`)
4. Decades (`the 1990s`)
5. Deadline phrases (`by 2030`, `before 2025`)
6. Duration phrases (`over 10 years`, `within 5 years`)
7. Relative expressions (`next quarter`, `last year`)
8. Plain years (`2024`)

Relative expressions are never resolved to absolute dates.

---

## Exact Deduplication

`_deduplicate.deduplicate_claims(claims)` uses the key:

```
"{source_id}\x00{parent_evidence_id_or_empty}\x00{normalized_text}"
```

- **Same-parent overlap**: two claims from different segments of the same parent evidence with the same text → collapse to canonical.
- **Same evidence item**: same evidence produces duplicate claims (e.g., via both sentence and clause paths) → collapse.
- **Cross-source**: same text from different sources → **never** collapse. Both are retained.

The canonical claim is the one with the lowest sort key: `(segment_index, evidence_start_char, clause_index, evidence_id, claim_id)`.

`DuplicateClaim` records the collapsed `claim_id`, the `canonical_claim_id`, `similarity=1.0`, and the deduplication strategy.

---

## Claim ID

Claim IDs are deterministic SHA256-based identifiers:

```
"clm-" + sha256(
    "\x00".join([
        source_id,
        evidence_id,
        parent_evidence_id or "",
        str(start_char),
        str(end_char),
        sha256(claim_text.encode())[:16],
        extractor_version,
        normalization_version,
    ])
)[:20]
```

The same claim re-extracted from the same evidence produces the same ID regardless of extraction order.

---

## Normalization

`extractor._normalize_claim(text)`:

1. NFC Unicode normalization
2. CRLF / CR → LF
3. Whitespace collapse (multiple spaces → single space, tabs → space)
4. Strip leading and trailing whitespace

Normalization does **not** change meaning: no lowercasing, no punctuation removal, no stop-word removal, no lemmatization.

---

## Configuration

`ClaimExtractionConfig` controls extraction behavior:

| Field | Default | Description |
|---|---|---|
| `minimum_claim_characters` | 10 | Reject claims shorter than this |
| `maximum_claim_characters` | 2000 | Reject claims longer than this |
| `split_clauses` | `True` | Split sentences on `;` and ` but ` |
| `preserve_questions` | `False` | Keep question-form text |
| `preserve_commands` | `False` | Keep imperative text |
| `include_rejections` | `True` | Include `ClaimRejection` records in result |
| `deduplicate_exact` | `True` | Collapse exact same-source duplicates |
| `normalize_whitespace` | `True` | Apply whitespace normalization |
| `normalization_version` | `"1"` | Part of claim ID computation |
| `extractor_version` | `"1"` | Part of claim ID computation |

`config.fingerprint` is a 16-hex-character SHA256 of the config dict. It is stable across process restarts and stored in diagnostics.

---

## Diagnostics

`ClaimExtractionDiagnostics` carries full pipeline accounting:

| Field | Description |
|---|---|
| `input_evidence_count` | Number of `RankedEvidence` items received |
| `input_ranked_count` | Same as above (ranked items only) |
| `claims_extracted` | Final claim count after deduplication |
| `claims_rejected` | Candidates that did not pass assertiveness filter |
| `duplicate_claims` | Claims collapsed by deduplication |
| `evidence_without_claims` | Evidence items that produced zero claims |
| `claims_by_type` | `MappingProxyType[str, int]` — count per `ClaimType` |
| `claims_by_modality` | `MappingProxyType[str, int]` — count per `ClaimModality` |
| `claims_by_polarity` | `MappingProxyType[str, int]` — count per `ClaimPolarity` |
| `rejection_reasons` | `MappingProxyType[str, int]` — count per `RejectionReason` |
| `configuration_fingerprint` | `config.fingerprint` |

All enum keys are always present with 0 counts. The sum of `claims_by_type.values()` equals `claims_extracted`.

---

## Guarantees

- **Determinism**: identical input → identical output (same claim IDs, same ordering).
- **No LLM**: the claims package has zero LLM imports.
- **No network**: no imports from `requests`, `httpx`, `ddgs`, or any network library.
- **No NLP libraries**: no `spacy`, `nltk`, `transformers`.
- **Lineage preserved**: every `ExtractedClaim` records `source_id`, `evidence_id`, `parent_evidence_id`, `segment_index`, `evidence_start_char`, `evidence_end_char`.
- **Immutability**: all contracts are `frozen=True` dataclasses.
- **No truth inference**: no claim carries a truth score, verification score, or contradiction status.
