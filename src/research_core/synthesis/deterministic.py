"""
DeterministicSynthesizer — rule-based, LLM-free structured synthesis (RC7).

Produces a SynthesisResult with five ordered sections:
  0. Summary
  1. Evidence-Derived Claims
  2. Quality and Coverage
  3. Research Gaps
  4. Limitations

Each section has a deterministic section_id:
  "sec-" + sha256(f"{title}\\x00{order}\\x00{version}").hexdigest()[:16]

Each citation in the claims section has a deterministic citation_id:
  "cit-" + sha256(claim_id + "\\x00" + evidence_id + "\\x00" + source_id
                  + "\\x00" + section_id + "\\x00" + version).hexdigest()[:20]

Claim wording is preserved exactly. No truth inference, consensus, or
contradiction resolution is performed. Output is identical for identical inputs.
"""

from __future__ import annotations

import hashlib

from research_core.claims.contracts import ExtractedClaim
from research_core.contracts.gaps import GapSeverity
from research_core.contracts.result import SynthesisResult
from research_core.protocols.synthesis import SynthesisInput
from research_core.synthesis.contracts import (
    _DEFAULT_CONFIG,
    SynthesisCitation,
    SynthesisConfig,
    SynthesisDiagnostics,
    SynthesisSection,
    SynthesisStatus,
)

_SYNTHESIZER_NAME = "DeterministicSynthesizer"
_SYNTHESIZER_VERSION = "1.0"
_SYNTHESIS_MODEL = f"{_SYNTHESIZER_NAME}/{_SYNTHESIZER_VERSION}"

_LIMITATIONS_BODY = (
    "This synthesis was produced deterministically from extracted claims and evidence. "
    "It does not imply verification, truth, consensus, or corroboration. "
    "Claim wording is preserved as extracted. Conflicting claims are not resolved."
)


def _section_id(title: str, order: int, version: str) -> str:
    return "sec-" + hashlib.sha256(
        f"{title}\x00{order}\x00{version}".encode()
    ).hexdigest()[:16]


def _citation_id(
    claim_id: str, evidence_id: str, source_id: str, section_id: str, version: str
) -> str:
    payload = "\x00".join([claim_id, evidence_id, source_id, section_id, version])
    return "cit-" + hashlib.sha256(payload.encode()).hexdigest()[:20]


class DeterministicSynthesizer:
    """Evidence-grounded, deterministic structured synthesizer.

    Builds five structured sections from the supplied SynthesisInput without
    calling any LLM, network service, or non-deterministic function. Output
    is identical for identical inputs.

    What this synthesizer does:
    - Groups extracted claims by evidence rank then claim_id for stability
    - Preserves claim wording exactly (no paraphrasing)
    - Reports quality diagnostics from RC6 when available
    - Reports gap counts and severity breakdowns
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
        inputs: SynthesisInput,
        *,
        config: SynthesisConfig | None = None,
    ) -> SynthesisResult:
        """Synthesize evidence and claims into a structured narrative.

        Returns a SynthesisResult with sections, citations, and backward-
        compatible narrative/key_findings. The narrative is always non-empty.
        """
        cfg = config if config is not None else _DEFAULT_CONFIG
        version = cfg.synthesizer_version

        n_sources = len(inputs.sources)
        n_evidence = len(inputs.evidence)
        n_claims = len(inputs.claims)
        gap_analysis = inputs.gap_analysis
        gaps = gap_analysis.gaps if gap_analysis is not None else ()
        n_gaps = len(gaps)

        # Evidence rank lookup: used for stable claim ordering
        evidence_rank: dict[str, int] = {
            re.normalized_evidence.evidence.evidence_id: re.rank
            for re in inputs.evidence
        }

        # Claims sorted by evidence rank then claim_id (stable, deterministic)
        def _claim_sort_key(c: ExtractedClaim) -> tuple[int, str]:
            return (evidence_rank.get(c.evidence_id, 999_999), c.claim_id)

        max_claims = cfg.maximum_claims_per_section
        sorted_claims = sorted(inputs.claims[:max_claims], key=_claim_sort_key)

        # --- Summary body ---
        if n_sources == 0:
            summary_body = (
                "No sources were retrieved. "
                "This synthesis cannot derive claims from the available input. "
                "Research gaps indicate missing coverage. "
                + _LIMITATIONS_BODY
            )
        else:
            critical_gaps = sum(1 for g in gaps if g.severity == GapSeverity.CRITICAL)
            high_gaps = sum(1 for g in gaps if g.severity == GapSeverity.HIGH)
            gap_note = ""
            if critical_gaps:
                gap_note += f" {critical_gaps} critical gap(s) require immediate attention."
            if high_gaps:
                gap_note += f" {high_gaps} high-severity gap(s) identified."
            summary_body = (
                f"The research produced {n_claims} claim(s) from "
                f"{n_evidence} evidence item(s) across {n_sources} source(s). "
                f"{n_gaps} research gap(s) were identified.{gap_note} "
                + _LIMITATIONS_BODY
            )

        # Assemble sections
        sections: list[SynthesisSection] = []
        citations_list: list[SynthesisCitation] = []
        claims_used_ids: set[str] = set()
        evidence_used_ids: set[str] = set()

        # Section 0: Summary
        if cfg.include_summary:
            sec_id_0 = _section_id("Summary", 0, version)
            sections.append(
                SynthesisSection(
                    section_id=sec_id_0,
                    title="Summary",
                    body=summary_body,
                    order=0,
                )
            )

        # Section 1: Evidence-Derived Claims
        if cfg.include_claims_section:
            sec_id_1 = _section_id("Evidence-Derived Claims", 1, version)
            claim_lines: list[str] = []
            claim_ids: list[str] = []
            ev_ids_in_section: list[str] = []
            src_ids_in_section: list[str] = []
            for i, ec in enumerate(sorted_claims, 1):
                claim_lines.append(f"{i}. {ec.claim_text}")
                claim_ids.append(ec.claim_id)
                if ec.evidence_id not in ev_ids_in_section:
                    ev_ids_in_section.append(ec.evidence_id)
                if ec.source_id not in src_ids_in_section:
                    src_ids_in_section.append(ec.source_id)
                claims_used_ids.add(ec.claim_id)
                evidence_used_ids.add(ec.evidence_id)
                cit_id = _citation_id(
                    ec.claim_id, ec.evidence_id, ec.source_id, sec_id_1, version
                )
                citations_list.append(
                    SynthesisCitation(
                        citation_id=cit_id,
                        claim_id=ec.claim_id,
                        evidence_id=ec.evidence_id,
                        source_id=ec.source_id,
                        section_id=sec_id_1,
                        label=f"[{i}]",
                    )
                )
            sections.append(
                SynthesisSection(
                    section_id=sec_id_1,
                    title="Evidence-Derived Claims",
                    body=(
                        "\n".join(claim_lines)
                        if claim_lines
                        else "No claims were extracted."
                    ),
                    claim_ids=tuple(claim_ids),
                    evidence_ids=tuple(ev_ids_in_section),
                    source_ids=tuple(src_ids_in_section),
                    order=1,
                )
            )

        # Section 2: Quality and Coverage
        if cfg.include_quality_section:
            sec_id_2 = _section_id("Quality and Coverage", 2, version)
            if gap_analysis is not None:
                qd = gap_analysis.quality_diagnostics
                cov = qd.coverage
                util = (
                    f"{cov.evidence_utilization_ratio:.1%}"
                    if cov.evidence_utilization_ratio is not None
                    else "Unavailable"
                )
                score_str = (
                    f"{qd.overall_score:.3f}"
                    if qd.overall_score is not None
                    else "Unavailable"
                )
                quality_body = (
                    f"Overall diagnostic status: {qd.overall_status.value}. "
                    f"Overall score: {score_str}. "
                    f"Sources: {cov.source_count}, evidence: {cov.evidence_count}, "
                    f"claims: {cov.claim_count}. "
                    f"Evidence utilization: {util}."
                )
            else:
                quality_body = (
                    "Quality diagnostics not available "
                    "(RC6 gap analyzer was not used)."
                )
            sections.append(
                SynthesisSection(
                    section_id=sec_id_2,
                    title="Quality and Coverage",
                    body=quality_body,
                    order=2,
                )
            )

        # Section 3: Research Gaps
        if cfg.include_gaps_section:
            sec_id_3 = _section_id("Research Gaps", 3, version)
            if gaps:
                gap_lines = [
                    f"{i}. [{g.severity.upper()}] {g.description}"
                    for i, g in enumerate(gaps, 1)
                ]
                gaps_body = "\n".join(gap_lines)
            else:
                gaps_body = "No research gaps were identified."
            sections.append(
                SynthesisSection(
                    section_id=sec_id_3,
                    title="Research Gaps",
                    body=gaps_body,
                    order=3,
                )
            )

        # Section 4: Limitations
        if cfg.include_limitations_section:
            sec_id_4 = _section_id("Limitations", 4, version)
            sections.append(
                SynthesisSection(
                    section_id=sec_id_4,
                    title="Limitations",
                    body=_LIMITATIONS_BODY,
                    order=4,
                )
            )

        # Diagnostics
        diagnostics = SynthesisDiagnostics(
            input_source_count=n_sources,
            input_evidence_count=n_evidence,
            input_claim_count=n_claims,
            input_gap_count=n_gaps,
            claims_used=len(claims_used_ids),
            claims_unused=max(0, n_claims - len(claims_used_ids)),
            evidence_used=len(evidence_used_ids),
            evidence_unused=max(0, n_evidence - len(evidence_used_ids)),
            sections_emitted=len(sections),
            citations_emitted=len(citations_list),
            configuration_fingerprint=cfg.fingerprint,
            synthesizer=_SYNTHESIZER_NAME,
            synthesizer_version=version,
        )

        # Backward-compat: narrative = summary body; key_findings = claim texts
        key_findings = tuple(c.claim_text for c in sorted_claims)

        return SynthesisResult(
            narrative=summary_body,
            key_findings=key_findings,
            synthesis_model=_SYNTHESIS_MODEL,
            synthesized_at=None,
            confidence=None,
            sections=tuple(sections),
            citations=tuple(citations_list),
            synthesis_diagnostics=diagnostics,
            synthesis_status=SynthesisStatus.COMPLETE,
        )
