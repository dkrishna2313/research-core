"""
RC7 regression tests for structured synthesis contracts.

Tests for SynthesisSection, SynthesisCitation, SynthesisDiagnostics,
SynthesisConfig, and the DeterministicSynthesizer's structured output.
"""

from __future__ import annotations

import hashlib

import pytest

from research_core.claims.contracts import (
    ClaimModality,
    ClaimPolarity,
    ClaimScope,
    ClaimType,
    ExtractedClaim,
)
from research_core.protocols.synthesis import SynthesisInput
from research_core.synthesis.contracts import (
    SynthesisCitation,
    SynthesisConfig,
    SynthesisDiagnostics,
    SynthesisSection,
)
from research_core.synthesis.deterministic import DeterministicSynthesizer


def _ec(
    claim_id: str,
    claim_text: str,
    evidence_id: str = "ev-1",
    source_id: str = "src-1",
) -> ExtractedClaim:
    return ExtractedClaim(
        claim_id=claim_id,
        claim_text=claim_text,
        normalized_text=claim_text,
        claim_type=ClaimType.FACTUAL,
        modality=ClaimModality.ASSERTED,
        polarity=ClaimPolarity.POSITIVE,
        scope=ClaimScope(),
        qualifiers=(),
        quantitative_expressions=(),
        temporal_expressions=(),
        attribution=None,
        source_id=source_id,
        evidence_id=evidence_id,
        parent_evidence_id=None,
        segment_index=None,
        evidence_start_char=0,
        evidence_end_char=len(claim_text),
        sentence_index=0,
        clause_index=0,
        extractor="test",
        extractor_version="1",
    )


def _minimal_inputs(**kw: object) -> SynthesisInput:
    from research_core.contracts.common import SourceType
    from research_core.contracts.sources import Source
    defaults: dict[str, object] = {
        "request_text": "test",
        "sources": (Source(source_id="src-1", source_type=SourceType.KNOWLEDGE),),
        "evidence": (),
        "claims": (),
    }
    defaults.update(kw)
    return SynthesisInput(**defaults)  # type: ignore[arg-type]


@pytest.mark.synthesis
class TestSynthesisSectionImmutability:
    def test_section_is_frozen(self) -> None:
        sec = SynthesisSection(section_id="sec-abc", title="Test Section")
        with pytest.raises((AttributeError, TypeError)):
            sec.title = "mutated"  # type: ignore[misc]

    def test_citation_is_frozen(self) -> None:
        cit = SynthesisCitation(
            citation_id="cit-abc",
            claim_id="cl-1",
            evidence_id="ev-1",
            source_id="src-1",
            section_id="sec-1",
        )
        with pytest.raises((AttributeError, TypeError)):
            cit.label = "mutated"  # type: ignore[misc]

    def test_diagnostics_is_frozen(self) -> None:
        diag = SynthesisDiagnostics(
            input_source_count=1,
            input_evidence_count=1,
            input_claim_count=0,
            input_gap_count=0,
            claims_used=0,
            claims_unused=0,
            evidence_used=0,
            evidence_unused=1,
            sections_emitted=5,
            citations_emitted=0,
            configuration_fingerprint="abc",
            synthesizer="test",
            synthesizer_version="1",
        )
        with pytest.raises((AttributeError, TypeError)):
            diag.synthesizer = "mutated"  # type: ignore[misc]


@pytest.mark.synthesis
class TestSynthesisCitationIdFormula:
    def test_citation_id_formula(self) -> None:
        claim_id = "cl-001"
        evidence_id = "ev-001"
        source_id = "src-001"
        version = "1"
        # Claims go in the "Evidence-Derived Claims" section (order=1)
        section_title = "Evidence-Derived Claims"
        section_order = 1
        section_id = "sec-" + hashlib.sha256(
            f"{section_title}\x00{section_order}\x00{version}".encode()
        ).hexdigest()[:16]
        expected_payload = "\x00".join(
            [claim_id, evidence_id, source_id, section_id, version]
        )
        expected = "cit-" + hashlib.sha256(expected_payload.encode()).hexdigest()[:20]
        synth = DeterministicSynthesizer()
        ec = _ec(claim_id, "Some claim text.", evidence_id, source_id)
        result = synth.synthesize(_minimal_inputs(claims=(ec,)))
        assert len(result.citations) == 1
        assert result.citations[0].citation_id == expected

    def test_distinct_claims_get_distinct_citation_ids(self) -> None:
        ec1 = _ec("cl-1", "Claim one.", "ev-1", "src-1")
        ec2 = _ec("cl-2", "Claim two.", "ev-2", "src-1")
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_minimal_inputs(claims=(ec1, ec2)))
        ids = [c.citation_id for c in result.citations]
        assert len(set(ids)) == len(ids)

    def test_citation_id_stable_across_instances(self) -> None:
        ec = _ec("cl-1", "Some claim.")
        r1 = DeterministicSynthesizer().synthesize(_minimal_inputs(claims=(ec,)))
        r2 = DeterministicSynthesizer().synthesize(_minimal_inputs(claims=(ec,)))
        assert r1.citations[0].citation_id == r2.citations[0].citation_id


@pytest.mark.synthesis
class TestSynthesisDiagnosticsReconcile:
    def test_diagnostics_counts_match_sections(self) -> None:
        synth = DeterministicSynthesizer()
        ec1 = _ec("cl-1", "Revenue was $10 million.")
        ec2 = _ec("cl-2", "Costs fell 5%.")
        result = synth.synthesize(_minimal_inputs(claims=(ec1, ec2)))
        diag = result.synthesis_diagnostics
        assert diag is not None
        assert diag.sections_emitted == len(result.sections)
        assert diag.citations_emitted == len(result.citations)

    def test_diagnostics_input_claim_count(self) -> None:
        synth = DeterministicSynthesizer()
        ec1 = _ec("cl-1", "First claim.")
        ec2 = _ec("cl-2", "Second claim.")
        result = synth.synthesize(_minimal_inputs(claims=(ec1, ec2)))
        diag = result.synthesis_diagnostics
        assert diag is not None
        assert diag.input_claim_count == 2

    def test_diagnostics_claims_used_all_present(self) -> None:
        synth = DeterministicSynthesizer()
        ec = _ec("cl-1", "Single claim.")
        result = synth.synthesize(_minimal_inputs(claims=(ec,)))
        diag = result.synthesis_diagnostics
        assert diag is not None
        assert diag.claims_used == 1
        assert diag.claims_unused == 0


@pytest.mark.synthesis
class TestSynthesisClaimPreservation:
    def test_all_used_claims_have_citations(self) -> None:
        synth = DeterministicSynthesizer()
        ec1 = _ec("cl-1", "First claim.")
        ec2 = _ec("cl-2", "Second claim.")
        result = synth.synthesize(_minimal_inputs(claims=(ec1, ec2)))
        cited_claim_ids = {c.claim_id for c in result.citations}
        assert "cl-1" in cited_claim_ids
        assert "cl-2" in cited_claim_ids

    def test_distinct_claims_not_merged(self) -> None:
        synth = DeterministicSynthesizer()
        text1 = "Revenue increased by $10 million."
        text2 = "Revenue decreased by $5 million."
        ec1 = _ec("cl-1", text1)
        ec2 = _ec("cl-2", text2, evidence_id="ev-2")
        result = synth.synthesize(_minimal_inputs(claims=(ec1, ec2)))
        claims_sec = next(s for s in result.sections if s.title == "Evidence-Derived Claims")
        assert text1 in claims_sec.body
        assert text2 in claims_sec.body

    def test_negation_preserved_in_section(self) -> None:
        synth = DeterministicSynthesizer()
        statement = "The treatment did not reduce mortality rates."
        ec = _ec("cl-1", statement)
        result = synth.synthesize(_minimal_inputs(claims=(ec,)))
        claims_sec = next(s for s in result.sections if s.title == "Evidence-Derived Claims")
        assert statement in claims_sec.body

    def test_modality_preserved_in_section(self) -> None:
        synth = DeterministicSynthesizer()
        statement = "Demand may increase significantly over the next decade."
        ec = _ec("cl-1", statement)
        result = synth.synthesize(_minimal_inputs(claims=(ec,)))
        claims_sec = next(s for s in result.sections if s.title == "Evidence-Derived Claims")
        assert statement in claims_sec.body


@pytest.mark.synthesis
class TestSynthesisConfigFingerprint:
    def test_fingerprint_is_deterministic(self) -> None:
        cfg = SynthesisConfig()
        assert cfg.fingerprint == cfg.fingerprint

    def test_different_configs_different_fingerprints(self) -> None:
        cfg1 = SynthesisConfig(synthesizer_version="1")
        cfg2 = SynthesisConfig(synthesizer_version="2")
        assert cfg1.fingerprint != cfg2.fingerprint

    def test_same_config_same_fingerprint_across_instances(self) -> None:
        fp1 = SynthesisConfig(synthesizer_version="test").fingerprint
        fp2 = SynthesisConfig(synthesizer_version="test").fingerprint
        assert fp1 == fp2

    def test_config_in_diagnostics_fingerprint(self) -> None:
        synth = DeterministicSynthesizer()
        cfg = SynthesisConfig()
        result = synth.synthesize(_minimal_inputs(), config=cfg)
        diag = result.synthesis_diagnostics
        assert diag is not None
        assert diag.configuration_fingerprint == cfg.fingerprint


@pytest.mark.synthesis
class TestSynthesisSectionIdFormula:
    def test_section_id_formula(self) -> None:
        title = "Summary"
        order = 0
        version = "1"
        expected = "sec-" + hashlib.sha256(
            f"{title}\x00{order}\x00{version}".encode()
        ).hexdigest()[:16]
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_minimal_inputs())
        summary_sec = next(s for s in result.sections if s.title == "Summary")
        assert summary_sec.section_id == expected

    def test_section_id_stable_across_instances(self) -> None:
        r1 = DeterministicSynthesizer().synthesize(_minimal_inputs())
        r2 = DeterministicSynthesizer().synthesize(_minimal_inputs())
        ids1 = {s.section_id for s in r1.sections}
        ids2 = {s.section_id for s in r2.sections}
        assert ids1 == ids2
