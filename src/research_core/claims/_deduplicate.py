"""
Exact claim deduplication.

RC5 implements exact deduplication only. Near-duplicate semantic collapse
is not performed.

Deduplication policy:
  Case 1 — Same normalized_text, same parent_evidence_id (overlapping segments):
    Collapse to canonical. Canonical = lowest segment_index, then lowest
    evidence_start_char, then evidence_id asc, then claim_id asc.

  Case 2 — Same normalized_text, same evidence_id (within one evidence item):
    Collapse to canonical. Canonical = lowest evidence_start_char, then
    clause_index asc, then claim_id asc.

  Case 3 — Same normalized_text, different source_id:
    Do NOT collapse. Cross-source duplicates retain independent lineage.
    Noted in diagnostics only.

Claims with different negation, modality, attribution, or numeric values
are always preserved separately even when sentence text is similar.
"""

from __future__ import annotations

from research_core.claims.contracts import DuplicateClaim, ExtractedClaim


def deduplicate_claims(
    claims: list[ExtractedClaim],
) -> tuple[list[ExtractedClaim], list[DuplicateClaim]]:
    """Collapse exact duplicates according to the three-case policy.

    Returns (canonical_claims, duplicate_records).
    Canonical selection is deterministic: does not depend on input order.
    """
    # Group by (normalized_text, source_id, parent_evidence_id_or_evidence_id)
    canonical: dict[str, ExtractedClaim] = {}
    duplicates: list[DuplicateClaim] = []

    for claim in sorted(claims, key=_canonical_sort_key):
        dedup_key = _dedup_key(claim)
        if dedup_key in canonical:
            existing = canonical[dedup_key]
            method = _dedup_method(claim, existing)
            duplicates.append(
                DuplicateClaim(
                    claim_id=claim.claim_id,
                    canonical_claim_id=existing.claim_id,
                    method=method,
                    reason=f"identical normalized_text within {method}",
                    similarity=1.0,
                )
            )
        else:
            canonical[dedup_key] = claim

    return list(canonical.values()), duplicates


def _dedup_key(claim: ExtractedClaim) -> str:
    """Build the deduplication key for a claim.

    Claims from different source_ids are never collapsed, so source_id is
    always part of the key.

    For same-parent overlap: group by (source_id, parent_evidence_id, normalized_text)
    For same-evidence:        group by (source_id, evidence_id, normalized_text)
    For cross-source:         source_id differs → keys always differ → no collapse
    """
    norm = claim.normalized_text
    source = claim.source_id
    # If segmented, group by parent; otherwise group by evidence_id
    if claim.parent_evidence_id is not None:
        scope = f"parent:{claim.parent_evidence_id}"
    else:
        scope = f"ev:{claim.evidence_id}"
    return f"{source}\x00{scope}\x00{norm}"


def _canonical_sort_key(claim: ExtractedClaim) -> tuple[int, int, int, str, str]:
    """Sort key that produces the canonical representative first.

    Precedence:
      1. Lowest segment_index (unsegmented = 0)
      2. Lowest evidence_start_char
      3. Lowest clause_index
      4. evidence_id asc
      5. claim_id asc (tie-break)
    """
    seg_idx = claim.segment_index if claim.segment_index is not None else 0
    return (
        seg_idx,
        claim.evidence_start_char,
        claim.clause_index,
        claim.evidence_id,
        claim.claim_id,
    )


def _dedup_method(claim: ExtractedClaim, canonical: ExtractedClaim) -> str:
    """Determine the duplication method label."""
    if (
        claim.parent_evidence_id is not None
        and canonical.parent_evidence_id is not None
        and claim.parent_evidence_id == canonical.parent_evidence_id
    ):
        return "exact_overlap"
    if claim.evidence_id == canonical.evidence_id:
        return "exact_same_evidence"
    return "exact_same_parent"
