"""
DeterministicSynthesizer — rule-based, LLM-free synthesis.

Produces a mechanically derived SynthesisResult from extracted claims,
evidence, and gaps. Preserves claim wording exactly. Does not infer truth,
consensus, contradiction resolution, or recommendations.

Synthesis is provider-based: this implementation satisfies the Synthesizer
protocol structurally without inheriting from any base class.

Output is identical for identical inputs. No randomness, timestamps,
object identity, or network access affects the result.
"""

from __future__ import annotations

from research_core.contracts.claims import Claim
from research_core.contracts.contradictions import Contradiction
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import OpenQuestion, ResearchGap
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import SynthesisResult

_SYNTHESIZER_NAME = "DeterministicSynthesizer"
_SYNTHESIZER_VERSION = "1.0"
_SYNTHESIS_MODEL = f"{_SYNTHESIZER_NAME}/{_SYNTHESIZER_VERSION}"

_LIMITATIONS_TEXT = (
    "This synthesis was produced deterministically from extracted claims and evidence. "
    "It does not imply verification, truth, consensus, or corroboration. "
    "Claim wording is preserved as extracted. Conflicting claims are not resolved."
)


class DeterministicSynthesizer:
    """Evidence-grounded, deterministic synthesizer.

    Builds a narrative and key findings from the supplied claims and evidence
    without calling any LLM, network service, or non-deterministic function.
    Output is identical for identical inputs.

    What this synthesizer does:
    - Groups claims by evidence order
    - Preserves claim wording exactly (no paraphrasing)
    - Reports counts and diagnostic statuses
    - Includes limitations text

    What this synthesizer does not do:
    - Infer truth, consensus, or corroboration
    - Resolve contradictions
    - Generate recommendations
    - Merge materially different claims
    - Remove negation, modality, quantities, or attribution
    """

    def synthesize(
        self,
        request: ResearchRequest,
        evidence: tuple[EvidenceItem, ...],
        claims: tuple[Claim, ...],
        contradictions: tuple[Contradiction, ...],
        gaps: tuple[ResearchGap, ...],
        open_questions: tuple[OpenQuestion, ...],
    ) -> SynthesisResult:
        """Synthesize evidence and claims into a structured narrative.

        Returns a SynthesisResult with a mechanically derived narrative
        and key findings. The narrative is always non-empty.
        """
        n_claims = len(claims)
        n_evidence = len(evidence)
        n_sources = len({ev.source_id for ev in evidence})
        n_gaps = len(gaps)
        n_contradictions = len(contradictions)

        # --- Summary sentence ---
        if n_evidence == 0:
            summary = (
                "No evidence was retrieved. "
                "This synthesis cannot derive claims from the available input. "
                "Research gaps indicate missing coverage."
            )
        else:
            summary = (
                f"The research produced {n_claims} claim(s) from "
                f"{n_evidence} evidence item(s) across {n_sources} source(s). "
                f"{n_gaps} research gap(s) were identified."
            )

        # --- Gap summary ---
        gap_parts: list[str] = []
        if gaps:
            critical = sum(1 for g in gaps if g.severity == "critical")
            high = sum(1 for g in gaps if g.severity == "high")
            label_parts: list[str] = []
            if critical:
                label_parts.append(f"{critical} critical")
            if high:
                label_parts.append(f"{high} high-severity")
            if label_parts:
                gap_parts.append(
                    f"Notable gap(s): {', '.join(label_parts)} gap(s) require attention."
                )

        # --- Contradiction notice ---
        contradiction_part = ""
        if n_contradictions > 0:
            contradiction_part = (
                f"{n_contradictions} contradiction(s) were detected in the evidence. "
                "Contradictions are not resolved by this synthesizer."
            )

        # --- Assemble narrative ---
        parts: list[str] = [summary]
        parts.extend(gap_parts)
        if contradiction_part:
            parts.append(contradiction_part)
        parts.append(_LIMITATIONS_TEXT)
        narrative = " ".join(parts)

        # --- Key findings: claim statements in evidence-order, then claim_id for stability ---
        evidence_rank: dict[str, int] = {ev.evidence_id: i for i, ev in enumerate(evidence)}

        def _claim_sort_key(c: Claim) -> tuple[int, str]:
            min_rank = min(
                (evidence_rank.get(eid, 999_999) for eid in c.supporting_evidence_ids),
                default=999_999,
            )
            return (min_rank, c.claim_id)

        key_findings = tuple(cl.statement for cl in sorted(claims, key=_claim_sort_key))

        return SynthesisResult(
            narrative=narrative,
            key_findings=key_findings,
            synthesis_model=_SYNTHESIS_MODEL,
            synthesized_at=None,
            confidence=None,
        )
