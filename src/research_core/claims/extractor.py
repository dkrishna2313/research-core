"""
ClaimExtractor protocol and DeterministicClaimExtractor implementation.

DeterministicClaimExtractor is a rule-based extractor that requires no
optional dependencies and makes no network or LLM calls. It is English-
oriented and uses the standard library only.

Processing order follows evidence rank (rank 1 first). Ranking score is
not used as a truth signal — it is used only for deterministic ordering.
Low-ranked evidence is never skipped by default.

ClaimExtractor is a separate protocol from the research_core.protocols.analysis
ClaimExtractor — it accepts Sequence[RankedEvidence] rather than a raw
evidence pool, and returns ClaimExtractionResult rather than tuple[Claim, ...].
"""

from __future__ import annotations

import hashlib
import re
import types
import unicodedata
from collections import Counter
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from research_core.claims._candidate import is_assertive, segment_clauses, segment_sentences
from research_core.claims._classify import (
    classify_claim,
    detect_modality,
    detect_polarity,
    extract_attribution,
    extract_quantitative,
    extract_temporal,
)
from research_core.claims._deduplicate import deduplicate_claims
from research_core.claims.config import ClaimExtractionConfig
from research_core.claims.contracts import (
    ClaimExtractionDiagnostics,
    ClaimExtractionResult,
    ClaimModality,
    ClaimPolarity,
    ClaimRejection,
    ClaimScope,
    ClaimType,
    DuplicateClaim,
    ExtractedClaim,
    RejectionReason,
    TemporalExpression,
)
from research_core.contracts.common import EMPTY_METADATA
from research_core.normalization.contracts import RankedEvidence

_DEFAULT_CONFIG = ClaimExtractionConfig()


@runtime_checkable
class ClaimExtractor(Protocol):
    """Protocol for extracting claims from ranked evidence.

    This is distinct from research_core.protocols.analysis.ClaimExtractor,
    which operates on raw evidence pools and ResearchRequest objects.
    This protocol operates on the RC4 ranked evidence layer.
    """

    def extract(
        self,
        ranked_evidence: Sequence[RankedEvidence],
        *,
        config: ClaimExtractionConfig | None = None,
    ) -> ClaimExtractionResult:
        """Extract claims from a ranked evidence sequence."""
        ...


class DeterministicClaimExtractor:
    """Rule-based deterministic claim extractor.

    Requires no optional dependencies. No LLM, no NLP library, no network.
    English-oriented sentence segmentation.

    Extraction is deterministic: identical ranked_evidence + identical config
    produces identical ClaimExtractionResult including identical claim IDs
    and ordering.

    Ranking score is used only for processing order (rank 1 first). It is
    never used as a truth score or to skip evidence.
    """

    NAME = "DeterministicClaimExtractor"
    VERSION = "1"

    def extract(
        self,
        ranked_evidence: Sequence[RankedEvidence],
        *,
        config: ClaimExtractionConfig | None = None,
    ) -> ClaimExtractionResult:
        """Extract claims from a ranked evidence sequence.

        Empty ranked_evidence returns a valid ClaimExtractionResult with
        zero claims and accurate diagnostics. This is not an error condition.
        """
        cfg = config or _DEFAULT_CONFIG

        all_claims: list[ExtractedClaim] = []
        all_rejections: list[ClaimRejection] = []
        total_sentences = 0
        total_clauses = 0
        evidence_without_claims = 0

        # Process in rank order for determinism. rank is 1-based.
        for ranked_item in sorted(ranked_evidence, key=lambda r: r.rank):
            item_claims, item_rejections, n_sents, n_clauses = self._process_item(
                ranked_item, cfg
            )
            total_sentences += n_sents
            total_clauses += n_clauses
            if not item_claims:
                evidence_without_claims += 1
            all_claims.extend(item_claims)
            all_rejections.extend(item_rejections)

        # Deduplicate
        if cfg.deduplicate_exact and all_claims:
            final_claims, duplicates = deduplicate_claims(all_claims)
        else:
            final_claims = all_claims
            duplicates = []

        # Build diagnostics
        diagnostics = _build_diagnostics(
            claims=final_claims,
            duplicates=duplicates,
            rejections=all_rejections,
            input_count=len(ranked_evidence),
            sentence_count=total_sentences,
            clause_count=total_clauses,
            evidence_without_claims=evidence_without_claims,
            cfg=cfg,
            extractor_name=self.NAME,
            extractor_version=self.VERSION,
        )

        return ClaimExtractionResult(
            claims=tuple(final_claims),
            duplicates=tuple(duplicates),
            rejections=tuple(all_rejections) if cfg.include_rejections else (),
            diagnostics=diagnostics,
            metadata=EMPTY_METADATA,
        )

    def _process_item(
        self,
        ranked: RankedEvidence,
        cfg: ClaimExtractionConfig,
    ) -> tuple[list[ExtractedClaim], list[ClaimRejection], int, int]:
        """Extract claims from one ranked evidence item.

        Returns (claims, rejections, sentence_count, clause_count).
        """
        norm_ev = ranked.normalized_evidence
        evidence = norm_ev.evidence
        source = norm_ev.source
        parent_evidence_id = norm_ev.parent_evidence_id
        segment_index = norm_ev.segment_index

        text = evidence.content
        sentences = segment_sentences(text)

        claims: list[ExtractedClaim] = []
        rejections: list[ClaimRejection] = []
        clause_count = 0

        for sent_idx, (sent_text, sent_start, _sent_end) in enumerate(sentences):
            if cfg.split_clauses:
                clauses = segment_clauses(sent_text, sent_start, cfg.minimum_claim_characters)
            else:
                clauses = [(sent_text, sent_start, sent_start + len(sent_text))]

            clause_count += len(clauses)

            for clause_idx, (clause_text, clause_start, clause_end) in enumerate(clauses):
                # Length bounds check
                if len(clause_text) < cfg.minimum_claim_characters:
                    rejections.append(
                        ClaimRejection(
                            evidence_id=evidence.evidence_id,
                            candidate_text=clause_text,
                            start_char=clause_start,
                            end_char=clause_end,
                            reason=RejectionReason.TOO_SHORT,
                            sentence_index=sent_idx,
                            clause_index=clause_idx,
                        )
                    )
                    continue

                if len(clause_text) > cfg.maximum_claim_characters:
                    rejections.append(
                        ClaimRejection(
                            evidence_id=evidence.evidence_id,
                            candidate_text=clause_text[: cfg.minimum_claim_characters],
                            start_char=clause_start,
                            end_char=clause_end,
                            reason=RejectionReason.TOO_SHORT,
                            sentence_index=sent_idx,
                            clause_index=clause_idx,
                        )
                    )
                    continue

                # Assertiveness check
                assertive, rejection_reason = is_assertive(
                    clause_text, cfg.minimum_claim_characters
                )

                if not assertive:
                    reason = rejection_reason or RejectionReason.NO_ASSERTION
                    # Respect preserve_questions / preserve_commands settings
                    if (
                        reason == RejectionReason.QUESTION and cfg.preserve_questions
                        or reason == RejectionReason.COMMAND and cfg.preserve_commands
                    ):
                        pass  # fall through to extraction
                    else:
                        rejections.append(
                            ClaimRejection(
                                evidence_id=evidence.evidence_id,
                                candidate_text=clause_text,
                                start_char=clause_start,
                                end_char=clause_end,
                                reason=reason,
                                sentence_index=sent_idx,
                                clause_index=clause_idx,
                            )
                        )
                        continue

                # Extract linguistic features
                quant_exprs = extract_quantitative(clause_text)
                temporal_exprs: list[TemporalExpression] = extract_temporal(clause_text)
                attribution = extract_attribution(clause_text)
                modality, modal_qualifiers = detect_modality(clause_text)
                polarity = detect_polarity(clause_text)
                claim_type = classify_claim(clause_text, quant_exprs)

                # Normalize
                normalized = _normalize_claim(clause_text)

                # Claim ID
                claim_id = _make_claim_id(
                    source_id=source.source_id,
                    evidence_id=evidence.evidence_id,
                    parent_evidence_id=parent_evidence_id,
                    start_char=clause_start,
                    end_char=clause_end,
                    normalized_text=normalized,
                    extractor_version=self.VERSION,
                    normalization_version=cfg.normalization_version,
                )

                claims.append(
                    ExtractedClaim(
                        claim_id=claim_id,
                        claim_text=clause_text,
                        normalized_text=normalized,
                        claim_type=claim_type,
                        modality=modality,
                        polarity=polarity,
                        scope=ClaimScope(),
                        qualifiers=tuple(modal_qualifiers),
                        quantitative_expressions=tuple(quant_exprs),
                        temporal_expressions=tuple(temporal_exprs),
                        attribution=attribution,
                        source_id=source.source_id,
                        evidence_id=evidence.evidence_id,
                        parent_evidence_id=parent_evidence_id,
                        segment_index=segment_index,
                        evidence_start_char=clause_start,
                        evidence_end_char=clause_end,
                        sentence_index=sent_idx,
                        clause_index=clause_idx,
                        extractor=self.NAME,
                        extractor_version=self.VERSION,
                        metadata=EMPTY_METADATA,
                    )
                )

        return claims, rejections, len(sentences), clause_count


def _normalize_claim(text: str) -> str:
    """Conservative normalization that preserves all meaning-bearing content.

    Steps:
    1. Unicode NFC normalization
    2. Normalize line endings to space
    3. Collapse repeated internal whitespace
    4. Trim surrounding whitespace

    Does NOT:
    - Remove negation
    - Remove modal verbs
    - Change tense
    - Remove numbers, units, or currency
    - Resolve pronouns
    - Paraphrase or summarize
    """
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _make_claim_id(
    source_id: str,
    evidence_id: str,
    parent_evidence_id: str | None,
    start_char: int,
    end_char: int,
    normalized_text: str,
    extractor_version: str,
    normalization_version: str,
) -> str:
    """Generate a deterministic, cross-process-stable claim ID.

    Inputs:
    - source_id          — identifies the source
    - evidence_id        — identifies the evidence item (segment or parent)
    - parent_evidence_id — segment lineage (empty string if None)
    - start_char         — character offset within evidence content
    - end_char           — character offset within evidence content
    - normalized_text    — content identity (SHA256 of this)
    - extractor_version  — version of extraction algorithm
    - normalization_version — version of normalization algorithm

    Changes to any of the above change the ID.
    Changes to metadata, rank, or score do NOT change the ID.

    Formula:
      content_hash = sha256(normalized_text)
      key = null-separated concatenation of all inputs
      claim_id = "clm-" + sha256(key)[:20]
    """
    content_hash = hashlib.sha256(normalized_text.encode()).hexdigest()
    key = "\x00".join(
        [
            source_id,
            evidence_id,
            parent_evidence_id or "",
            str(start_char),
            str(end_char),
            content_hash,
            extractor_version,
            normalization_version,
        ]
    )
    return "clm-" + hashlib.sha256(key.encode()).hexdigest()[:20]


def _build_diagnostics(
    claims: list[ExtractedClaim],
    duplicates: list[DuplicateClaim],
    rejections: list[ClaimRejection],
    input_count: int,
    sentence_count: int,
    clause_count: int,
    evidence_without_claims: int,
    cfg: ClaimExtractionConfig,
    extractor_name: str,
    extractor_version: str,
) -> ClaimExtractionDiagnostics:
    """Build diagnostics from extraction results."""
    type_counts: Counter[str] = Counter()
    modality_counts: Counter[str] = Counter()
    polarity_counts: Counter[str] = Counter()

    for claim in claims:
        type_counts[str(claim.claim_type)] += 1
        modality_counts[str(claim.modality)] += 1
        polarity_counts[str(claim.polarity)] += 1

    rejection_counts: Counter[str] = Counter()
    for rej in rejections:
        rejection_counts[str(rej.reason)] += 1

    # Ensure all enum values appear in the dicts (with 0 counts)
    for t in ClaimType:
        type_counts.setdefault(str(t), 0)
    for m in ClaimModality:
        modality_counts.setdefault(str(m), 0)
    for p in ClaimPolarity:
        polarity_counts.setdefault(str(p), 0)
    for r in RejectionReason:
        rejection_counts.setdefault(str(r), 0)

    dup_count = len([d for d in duplicates if isinstance(d, object)])

    return ClaimExtractionDiagnostics(
        input_evidence_count=input_count,
        input_ranked_count=input_count,
        candidate_sentence_count=sentence_count,
        candidate_clause_count=clause_count,
        claims_extracted=len(claims),
        claims_rejected=len(rejections),
        duplicate_claims=dup_count,
        evidence_without_claims=evidence_without_claims,
        claims_by_type=types.MappingProxyType(dict(type_counts)),
        claims_by_modality=types.MappingProxyType(dict(modality_counts)),
        claims_by_polarity=types.MappingProxyType(dict(polarity_counts)),
        rejection_reasons=types.MappingProxyType(dict(rejection_counts)),
        configuration_fingerprint=cfg.fingerprint,
        extractor_name=extractor_name,
        extractor_version=extractor_version,
        metadata=EMPTY_METADATA,
    )
