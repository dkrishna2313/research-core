# Claim Contracts Reference — RC5

All types are in `research_core.claims`. All dataclasses are `frozen=True`. All enumerations are `StrEnum`.

---

## Enumerations

### `ClaimType`

Linguistic form of a claim. Classification uses a strict precedence order.

| Value | Description |
|---|---|
| `factual` | Default assertion; no special linguistic form detected |
| `quantitative` | Contains a non-trivial numeric expression |
| `causal` | Expresses a cause-and-effect relationship |
| `comparative` | Contains a comparison between two entities or states |
| `predictive` | Asserts a future state or forecast |
| `normative` | Expresses obligation, requirement, or recommendation |
| `definitional` | Defines or characterizes a concept |
| `unknown` | Fallback when form cannot be determined |

Classification precedence: NORMATIVE > PREDICTIVE > CAUSAL > COMPARATIVE > QUANTITATIVE > DEFINITIONAL > FACTUAL > UNKNOWN.

---

### `ClaimModality`

Modal force of a claim.

| Value | Description |
|---|---|
| `asserted` | Default; no modal language detected |
| `possible` | May, might, could |
| `probable` | Likely, probably, expected to |
| `required` | Must, shall, mandated |
| `recommended` | Should, ought to |
| `conditional` | If …, provided that |
| `unknown` | Fallback |

Modality precedence for detection: CONDITIONAL > REQUIRED > RECOMMENDED > PROBABLE > POSSIBLE > ASSERTED.

---

### `ClaimPolarity`

Negation status of a claim.

| Value | Description |
|---|---|
| `positive` | No negation detected |
| `negated` | Explicit negation present |
| `mixed` | Both negated and positive assertions present |
| `unknown` | Polarity could not be determined conservatively |

---

### `ClaimQualifierKind`

Category of a meaning-bearing modifier.

`modal` | `temporal` | `quantitative` | `comparative` | `conditional` | `exception` | `attribution` | `scope` | `other`

---

### `TemporalKind`

Category of a temporal expression.

`date` | `year` | `range` | `duration` | `relative` | `deadline` | `unknown`

---

### `RejectionReason`

Why a candidate was not emitted as a claim.

| Value | Description |
|---|---|
| `empty` | Text is empty after stripping |
| `too_short` | Below `minimum_claim_characters` |
| `too_long` | Above `maximum_claim_characters` |
| `heading` | Detected as a section heading |
| `question` | Ends with `?` and `preserve_questions=False` |
| `command` | Starts with imperative verb and `preserve_commands=False` |
| `fragment` | No subject-verb structure detected |
| `boilerplate` | Detected as navigational or structural text |
| `no_assertion` | No assertive content |
| `citation_only` | Contains only citation markers |
| `duplicate` | Exact duplicate collapsed by deduplication |
| `unsupported` | Future extension point |

---

## Sub-objects

### `ClaimQualifier`

A meaning-bearing modifier captured from the claim text.

| Field | Type | Description |
|---|---|---|
| `text` | `str` | The modifier text as it appears in the claim |
| `kind` | `ClaimQualifierKind` | Category of the modifier |
| `start_char` | `int` | Start offset in the claim text |
| `end_char` | `int` | End offset in the claim text |

Offsets reference `ExtractedClaim.claim_text`, not the evidence content.

---

### `QuantitativeExpression`

An explicit numeric expression extracted from a claim.

| Field | Type | Description |
|---|---|---|
| `text` | `str` | Full expression text including unit/currency |
| `value_text` | `str` | Numeric portion as a string (not parsed to float) |
| `unit` | `str` | Physical unit if present (`MW`, `km`, …) |
| `comparator` | `str` | Comparator if present (`more than`, `at least`, …) |
| `range_start` | `str` | Lower bound text for ranges |
| `range_end` | `str` | Upper bound text for ranges |
| `currency` | `str` | Currency symbol/code if present |
| `percentage` | `bool` | `True` if the expression is a percentage |
| `start_char` | `int` | Start offset in claim text |
| `end_char` | `int` | End offset in claim text |

Numeric values are never parsed to `float`. All values remain as text.

---

### `TemporalExpression`

An explicit time expression extracted from a claim.

| Field | Type | Description |
|---|---|---|
| `text` | `str` | Full expression text as it appears |
| `start_char` | `int` | Start offset in claim text |
| `end_char` | `int` | End offset in claim text |
| `kind` | `TemporalKind` | Category of temporal expression |

Relative expressions (`next quarter`, `last year`) are never resolved to absolute dates.

---

### `ClaimAttribution`

Explicit attribution captured from a claim.

| Field | Type | Description |
|---|---|---|
| `source_text` | `str` | Attributed speaker/organization as it appears |
| `reporting_verb` | `str` | Linking verb (`said`, `reported`, `found`, …) |
| `attributed_text` | `str` | The attributed proposition text |
| `start_char` | `int` | Start of attribution in claim text |
| `end_char` | `int` | End of attribution in claim text |

Attribution records the textual structure; it does not verify the source or the claim.

---

### `ClaimScope`

Conservative structural decomposition of a claim into subject/predicate/object/condition/exception. All fields are best-effort; empty string means the component was not identified.

| Field | Type |
|---|---|
| `subject_text` | `str` |
| `predicate_text` | `str` |
| `object_text` | `str` |
| `condition_text` | `str` |
| `exception_text` | `str` |

---

## Primary Contracts

### `ExtractedClaim`

A discrete assertion extracted from a ranked evidence item.

| Field | Type | Description |
|---|---|---|
| `claim_id` | `str` | Deterministic `"clm-" + sha256[...20]` |
| `claim_text` | `str` | Verbatim text span from evidence content |
| `normalized_text` | `str` | Conservative normalization (whitespace/Unicode NFC only) |
| `claim_type` | `ClaimType` | Linguistic classification |
| `modality` | `ClaimModality` | Modal force |
| `polarity` | `ClaimPolarity` | Negation status |
| `scope` | `ClaimScope` | Subject/predicate/object decomposition |
| `qualifiers` | `tuple[ClaimQualifier, ...]` | Meaning-bearing modifiers |
| `quantitative_expressions` | `tuple[QuantitativeExpression, ...]` | Numeric sub-expressions |
| `temporal_expressions` | `tuple[TemporalExpression, ...]` | Temporal sub-expressions |
| `attribution` | `ClaimAttribution \| None` | Attribution if detected |
| `source_id` | `str` | ID of the originating source |
| `evidence_id` | `str` | ID of the evidence item (segment or full) |
| `parent_evidence_id` | `str \| None` | Set when evidence is a segment |
| `segment_index` | `int \| None` | Set when evidence is a segment |
| `evidence_start_char` | `int` | Start offset within evidence content |
| `evidence_end_char` | `int` | End offset within evidence content |
| `sentence_index` | `int` | 0-based sentence index within evidence |
| `clause_index` | `int` | 0-based clause index within sentence |
| `extractor` | `str` | Extractor name |
| `extractor_version` | `str` | Extractor version |
| `metadata` | `Metadata` | Immutable `MappingProxyType` for extensions |

Validation invariants:
- `claim_id`, `claim_text`, `normalized_text`, `source_id`, `evidence_id` must be non-empty
- `0 <= evidence_start_char < evidence_end_char`
- `sentence_index >= 0`, `clause_index >= 0`
- `segment_index >= 0` if not `None`

No truth score, verification score, or contradiction status is present on this type.

---

### `DuplicateClaim`

Records a claim that was collapsed during deduplication.

| Field | Type | Description |
|---|---|---|
| `claim_id` | `str` | ID of the collapsed (non-canonical) claim |
| `canonical_claim_id` | `str` | ID of the retained canonical claim |
| `method` | `str` | Deduplication strategy applied (`exact_overlap`, `exact_same_evidence`, `exact_same_parent`) |
| `reason` | `str` | Human-readable description of why the claim was collapsed |
| `similarity` | `float` | Always `1.0` for exact deduplication |

---

### `ClaimRejection`

Records a candidate that did not pass the assertiveness filter.

| Field | Type | Description |
|---|---|---|
| `evidence_id` | `str` | Originating evidence item |
| `candidate_text` | `str` | The text that was rejected (truncated to `maximum_claim_characters` for TOO_LONG) |
| `start_char` | `int` | Start offset of the candidate within the evidence content |
| `end_char` | `int` | End offset of the candidate within the evidence content |
| `reason` | `RejectionReason` | Why it was rejected |
| `sentence_index` | `int` | 0-based sentence index within the evidence item |
| `clause_index` | `int` | 0-based clause index within the sentence |

---

### `ClaimExtractionDiagnostics`

Full pipeline accounting for a single extraction run.

| Field | Type | Description |
|---|---|---|
| `input_evidence_count` | `int` | Items received |
| `input_ranked_count` | `int` | Ranked items processed |
| `claims_extracted` | `int` | Final count after deduplication |
| `claims_rejected` | `int` | Candidates filtered out |
| `duplicate_claims` | `int` | Claims collapsed |
| `evidence_without_claims` | `int` | Items that produced zero claims |
| `claims_by_type` | `MappingProxyType[str, int]` | Count per `ClaimType` value |
| `claims_by_modality` | `MappingProxyType[str, int]` | Count per `ClaimModality` value |
| `claims_by_polarity` | `MappingProxyType[str, int]` | Count per `ClaimPolarity` value |
| `rejection_reasons` | `MappingProxyType[str, int]` | Count per `RejectionReason` value |
| `configuration_fingerprint` | `str` | 16-hex SHA256 of config |

All enum keys are always present with `0` counts even when unused. `sum(claims_by_type.values()) == claims_extracted`.

---

### `ClaimExtractionResult`

The return value of `ClaimExtractor.extract()`.

| Field | Type | Description |
|---|---|---|
| `claims` | `tuple[ExtractedClaim, ...]` | Extracted claims, sorted by evidence rank then position |
| `duplicates` | `tuple[DuplicateClaim, ...]` | Collapsed duplicate records |
| `rejections` | `tuple[ClaimRejection, ...]` | Rejected candidates (empty if `include_rejections=False`) |
| `diagnostics` | `ClaimExtractionDiagnostics` | Full pipeline accounting |

---

## Protocol

```python
@runtime_checkable
class ClaimExtractor(Protocol):
    def extract(
        self,
        ranked_evidence: Sequence[RankedEvidence],
        *,
        config: ClaimExtractionConfig | None = None,
    ) -> ClaimExtractionResult: ...
```

`DeterministicClaimExtractor` satisfies this protocol. `isinstance(extractor, ClaimExtractor)` returns `True`.

---

## Serialization

All contracts are compatible with `research_core.contracts.serialization.serialize()`:

- `StrEnum` values → `str`
- `tuple` → `list`
- `MappingProxyType` → `dict`
- `None` → `null`
- Nested dataclasses → `dict`

The result is JSON-serializable with `json.dumps()`.

---

## Stability Guarantees

- `claim_id` computation is stable across minor version bumps as long as `extractor_version` and `normalization_version` remain `"1"`.
- `config.fingerprint` is stable: the same config dict always produces the same fingerprint.
- Enum string values match exactly what is stored in serialized output (e.g. `"factual"`, not `"ClaimType.FACTUAL"`).
