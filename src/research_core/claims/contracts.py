"""
RC5 claim-extraction contracts.

A claim is a discrete assertion extracted from evidence. It is not a fact,
a verified statement, or a model belief. Every extracted claim retains full
lineage to the evidence text from which it was derived.

None of these contracts perform truth inference, corroboration scoring,
contradiction detection, or synthesis.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from enum import StrEnum

from research_core.contracts.common import EMPTY_METADATA, Metadata, _to_proxy
from research_core.exceptions import ContractValidationError


class ClaimType(StrEnum):
    """Linguistic form of a claim.

    Classification precedence (checked in order, first match wins):
      NORMATIVE > PREDICTIVE > CAUSAL > COMPARATIVE > QUANTITATIVE >
      DEFINITIONAL > FACTUAL > UNKNOWN

    UNKNOWN is used when the assertion is preserved but the form is unclear.
    This classification describes linguistic structure, not factual certainty.
    """

    FACTUAL = "factual"
    QUANTITATIVE = "quantitative"
    CAUSAL = "causal"
    COMPARATIVE = "comparative"
    PREDICTIVE = "predictive"
    NORMATIVE = "normative"
    DEFINITIONAL = "definitional"
    UNKNOWN = "unknown"


class ClaimModality(StrEnum):
    """Modal force of a claim.

    Captures the epistemic or deontic strength expressed in the text.
    Modality is orthogonal to claim type — a NORMATIVE claim can also be
    CONDITIONAL; a QUANTITATIVE claim can be POSSIBLE.

    ASSERTED is the default when no modal language is detected.
    Modality must not be converted to a confidence score.
    """

    ASSERTED = "asserted"
    POSSIBLE = "possible"
    PROBABLE = "probable"
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"


class ClaimPolarity(StrEnum):
    """Negation status of a claim.

    POSITIVE  — no negation detected.
    NEGATED   — explicit negation present (not, never, no, cannot, …).
    MIXED     — both negated and positive assertions are present
                (e.g. "not only X but also Y", "reduced X but not Y").
    UNKNOWN   — polarity could not be determined conservatively.

    Negation must not be removed from normalized_text.
    """

    POSITIVE = "positive"
    NEGATED = "negated"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ClaimQualifierKind(StrEnum):
    """Category of a meaning-bearing modifier."""

    MODAL = "modal"
    TEMPORAL = "temporal"
    QUANTITATIVE = "quantitative"
    COMPARATIVE = "comparative"
    CONDITIONAL = "conditional"
    EXCEPTION = "exception"
    ATTRIBUTION = "attribution"
    SCOPE = "scope"
    OTHER = "other"


class TemporalKind(StrEnum):
    """Category of a temporal expression."""

    DATE = "date"
    YEAR = "year"
    RANGE = "range"
    DURATION = "duration"
    RELATIVE = "relative"
    DEADLINE = "deadline"
    UNKNOWN = "unknown"


class RejectionReason(StrEnum):
    """Why a candidate text was not emitted as a claim."""

    EMPTY = "empty"
    TOO_SHORT = "too_short"
    HEADING = "heading"
    QUESTION = "question"
    COMMAND = "command"
    FRAGMENT = "fragment"
    BOILERPLATE = "boilerplate"
    NO_ASSERTION = "no_assertion"
    CITATION_ONLY = "citation_only"
    DUPLICATE = "duplicate"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ClaimQualifier:
    """A meaning-bearing modifier extracted from claim text.

    start_char and end_char are offsets into the claim_text of the
    ExtractedClaim that contains this qualifier (not into evidence content).
    """

    text: str
    kind: ClaimQualifierKind
    start_char: int
    end_char: int

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ContractValidationError("ClaimQualifier.text must not be empty")
        if self.start_char < 0:
            raise ContractValidationError(
                f"ClaimQualifier.start_char must be >= 0, got {self.start_char}"
            )
        if self.end_char <= self.start_char:
            raise ContractValidationError(
                f"ClaimQualifier.end_char ({self.end_char}) must be > "
                f"start_char ({self.start_char})"
            )


@dataclass(frozen=True)
class QuantitativeExpression:
    """An explicit numeric expression extracted from a claim.

    Offsets (start_char, end_char) refer to positions within the claim_text
    of the containing ExtractedClaim, not to the evidence content string.

    value_text is the numeric portion as a string; the original full text
    (including comparator, unit, currency) is preserved in the text field.
    Numeric conversion is not performed — values remain as text.

    percentage=True indicates the expression is a percentage (e.g. "12%").
    """

    text: str
    value_text: str
    unit: str = ""
    comparator: str = ""
    range_start: str = ""
    range_end: str = ""
    currency: str = ""
    percentage: bool = False
    start_char: int = 0
    end_char: int = 0

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ContractValidationError("QuantitativeExpression.text must not be empty")
        if self.start_char < 0:
            raise ContractValidationError(
                f"QuantitativeExpression.start_char must be >= 0, got {self.start_char}"
            )
        if self.end_char <= self.start_char:
            raise ContractValidationError(
                f"QuantitativeExpression.end_char ({self.end_char}) must be > "
                f"start_char ({self.start_char})"
            )


@dataclass(frozen=True)
class TemporalExpression:
    """An explicit time expression extracted from a claim.

    Offsets refer to positions within the claim_text of the containing
    ExtractedClaim.

    Relative expressions (e.g. "next quarter") are preserved as text and
    are never resolved to absolute calendar dates.
    """

    text: str
    start_char: int
    end_char: int
    kind: TemporalKind

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ContractValidationError("TemporalExpression.text must not be empty")
        if self.start_char < 0:
            raise ContractValidationError(
                f"TemporalExpression.start_char must be >= 0, got {self.start_char}"
            )
        if self.end_char <= self.start_char:
            raise ContractValidationError(
                f"TemporalExpression.end_char ({self.end_char}) must be > "
                f"start_char ({self.start_char})"
            )


@dataclass(frozen=True)
class ClaimAttribution:
    """Explicit attribution captured from a claim.

    source_text is the attributed speaker/organization as it appears in the text.
    reporting_verb is the verb linking source to proposition ("said", "reported", …).
    attributed_text is the attributed proposition text.

    Offsets refer to the full claim_text of the containing ExtractedClaim.

    Attribution does not imply the source is trustworthy or the proposition is
    verified. It records only that the claim was explicitly attributed.
    """

    source_text: str
    reporting_verb: str
    attributed_text: str
    start_char: int
    end_char: int

    def __post_init__(self) -> None:
        if not self.source_text.strip():
            raise ContractValidationError("ClaimAttribution.source_text must not be empty")
        if self.start_char < 0:
            raise ContractValidationError(
                f"ClaimAttribution.start_char must be >= 0, got {self.start_char}"
            )
        if self.end_char <= self.start_char:
            raise ContractValidationError(
                f"ClaimAttribution.end_char ({self.end_char}) must be > "
                f"start_char ({self.start_char})"
            )


@dataclass(frozen=True)
class ClaimScope:
    """Conservative structural decomposition of a claim.

    Fields are best-effort text extractions; empty string means the component
    was not identified. This is not full semantic-role labeling.
    """

    subject_text: str = ""
    predicate_text: str = ""
    object_text: str = ""
    condition_text: str = ""
    exception_text: str = ""


@dataclass(frozen=True)
class ExtractedClaim:
    """A discrete assertion extracted from a ranked evidence item.

    claim_text is the verbatim text span from
    evidence.content[evidence_start_char:evidence_end_char].
    normalized_text is a conservative normalization of claim_text (whitespace, Unicode NFC)
    — no semantic changes, no negation removal, no modal removal.

    Offsets (evidence_start_char, evidence_end_char) are character positions within
    the evidence.content string of the evidence item referenced by evidence_id.
    When evidence comes from a segment, offsets are local to the segment content.

    parent_evidence_id and segment_index are set only when evidence_id refers to a
    segment produced by the RC4 segmenter. For unsegmented evidence both are None.

    No truth score, verification score, contradiction status, or synthesis text
    is present on this contract.
    """

    claim_id: str
    claim_text: str
    normalized_text: str
    claim_type: ClaimType
    modality: ClaimModality
    polarity: ClaimPolarity
    scope: ClaimScope
    qualifiers: tuple[ClaimQualifier, ...]
    quantitative_expressions: tuple[QuantitativeExpression, ...]
    temporal_expressions: tuple[TemporalExpression, ...]
    attribution: ClaimAttribution | None
    source_id: str
    evidence_id: str
    parent_evidence_id: str | None
    segment_index: int | None
    evidence_start_char: int
    evidence_end_char: int
    sentence_index: int
    clause_index: int
    extractor: str
    extractor_version: str
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise ContractValidationError("ExtractedClaim.claim_id must not be empty")
        if not self.claim_text.strip():
            raise ContractValidationError("ExtractedClaim.claim_text must not be empty")
        if not self.normalized_text.strip():
            raise ContractValidationError("ExtractedClaim.normalized_text must not be empty")
        if not self.source_id.strip():
            raise ContractValidationError("ExtractedClaim.source_id must not be empty")
        if not self.evidence_id.strip():
            raise ContractValidationError("ExtractedClaim.evidence_id must not be empty")
        if self.evidence_start_char < 0:
            raise ContractValidationError(
                f"evidence_start_char must be >= 0, got {self.evidence_start_char}"
            )
        if self.evidence_end_char <= self.evidence_start_char:
            raise ContractValidationError(
                f"evidence_end_char ({self.evidence_end_char}) must be > "
                f"evidence_start_char ({self.evidence_start_char})"
            )
        if self.sentence_index < 0:
            raise ContractValidationError(
                f"sentence_index must be >= 0, got {self.sentence_index}"
            )
        if self.clause_index < 0:
            raise ContractValidationError(
                f"clause_index must be >= 0, got {self.clause_index}"
            )
        if self.segment_index is not None and self.segment_index < 0:
            raise ContractValidationError(
                f"segment_index must be >= 0 when set, got {self.segment_index}"
            )
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class DuplicateClaim:
    """Records that a claim was identified as a duplicate of another.

    method describes how the duplicate was detected:
      "exact_overlap"       — identical normalized_text from overlapping segments
                              of the same parent evidence
      "exact_same_evidence" — identical normalized_text within the same evidence item
      "exact_cross_source"  — noted for diagnostics; cross-source duplicates are
                              NOT collapsed by default

    similarity is 1.0 for all exact duplicates handled by RC5.
    """

    claim_id: str
    canonical_claim_id: str
    method: str
    reason: str
    similarity: float = 1.0


@dataclass(frozen=True)
class ClaimRejection:
    """Records a candidate text that was not emitted as a claim.

    Offsets are absolute positions within the evidence item's content string.
    """

    evidence_id: str
    candidate_text: str
    start_char: int
    end_char: int
    reason: RejectionReason
    sentence_index: int
    clause_index: int


@dataclass(frozen=True)
class ClaimExtractionDiagnostics:
    """Aggregate diagnostics from a claim extraction run.

    Reconciliation invariants:
      claims_extracted == sum(claims_by_type.values())
      claims_extracted == sum(claims_by_modality.values())
      claims_extracted == sum(claims_by_polarity.values())
      claims_rejected  == sum(rejection_reasons.values())

    claims_by_type / claims_by_modality / claims_by_polarity / rejection_reasons
    are MappingProxyType[str, int] keyed by the StrEnum .value strings.

    input_evidence_count == input_ranked_count in the current implementation
    (all ranked items are unique evidence items). The distinction is preserved
    for future extensions where the same evidence might appear at multiple ranks.
    """

    input_evidence_count: int
    input_ranked_count: int
    candidate_sentence_count: int
    candidate_clause_count: int
    claims_extracted: int
    claims_rejected: int
    duplicate_claims: int
    evidence_without_claims: int
    claims_by_type: types.MappingProxyType[str, int]
    claims_by_modality: types.MappingProxyType[str, int]
    claims_by_polarity: types.MappingProxyType[str, int]
    rejection_reasons: types.MappingProxyType[str, int]
    configuration_fingerprint: str
    extractor_name: str
    extractor_version: str
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class ClaimExtractionResult:
    """Complete output of a claim extraction run.

    An empty claims tuple is valid and does not indicate an error —
    some evidence simply contains no extractable assertions.

    rejections is empty when ClaimExtractionConfig.include_rejections is False.
    """

    claims: tuple[ExtractedClaim, ...]
    duplicates: tuple[DuplicateClaim, ...]
    rejections: tuple[ClaimRejection, ...]
    diagnostics: ClaimExtractionDiagnostics
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))
