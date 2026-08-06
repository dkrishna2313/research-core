"""
Tests for DeterministicSynthesizer (RC7 interface with SynthesisInput).
"""

from __future__ import annotations

import pytest

from research_core.claims.contracts import (
    ClaimModality,
    ClaimPolarity,
    ClaimScope,
    ClaimType,
    ExtractedClaim,
)
from research_core.contracts.gaps import GapSeverity, GapType, ResearchGap
from research_core.contracts.result import SynthesisResult
from research_core.protocols.synthesis import SynthesisInput
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


def _gap(gap_id: str = "gap-1", severity: GapSeverity = GapSeverity.MEDIUM) -> ResearchGap:
    return ResearchGap(
        gap_id=gap_id,
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        description="Insufficient coverage.",
        severity=severity,
    )


def _make_inputs(
    claims: tuple[ExtractedClaim, ...] = (),
    gap_analysis: object = None,
    request_text: str = "What is the impact?",
) -> SynthesisInput:
    """Build a minimal SynthesisInput for testing (no ranked evidence)."""
    from research_core.contracts.common import SourceType
    from research_core.contracts.sources import Source
    src = Source(source_id="src-1", source_type=SourceType.KNOWLEDGE)
    return SynthesisInput(
        request_text=request_text,
        sources=(src,) if claims else (),
        evidence=(),
        claims=claims,
        gap_analysis=gap_analysis,
    )


def _make_gap_analysis(gaps: tuple[ResearchGap, ...]) -> object:
    """Build a minimal GapAnalysisResult for testing."""
    import types as _types

    from research_core.analysis.contracts import (
        CoverageDiagnostics,
        DiagnosticStatus,
        DistributionDiagnostics,
        EvidenceConditionDiagnostics,
        GapAnalysisDiagnostics,
        GapAnalysisResult,
        QualityDiagnosticsResult,
    )
    from research_core.contracts.result import ResearchStatus

    quality = QualityDiagnosticsResult(
        overall_status=DiagnosticStatus.FAIL if gaps else DiagnosticStatus.PASS,
        overall_score=None,
        dimensions=(),
        coverage=CoverageDiagnostics(
            source_count=1,
            evidence_count=1,
            ranked_evidence_count=1,
            claim_count=len(gaps),
            claims_with_evidence=0,
            claims_without_evidence=0,
            evidence_with_claims=0,
            evidence_without_claims=1,
            unique_parent_evidence_count=1,
            segmented_evidence_count=0,
            sources_with_claims=0,
            sources_without_claims=1,
            claim_coverage_ratio=None,
            evidence_utilization_ratio=None,
        ),
        distribution=DistributionDiagnostics(
            unique_source_count=1,
            unique_provider_count=1,
            largest_source_share=1.0,
            largest_provider_share=1.0,
            source_diversity_score=None,
            provider_diversity_score=None,
            evidence_per_source=_types.MappingProxyType({}),
            evidence_per_provider=_types.MappingProxyType({}),
        ),
        evidence_conditions=EvidenceConditionDiagnostics(
            truncated_evidence_count=0,
            duplicate_evidence_count=0,
            near_duplicate_evidence_count=0,
            missing_retrieval_score_count=0,
            missing_retrieval_rank_count=0,
            invalid_lineage_count=0,
        ),
        gap_count=len(gaps),
        critical_gap_count=sum(1 for g in gaps if g.severity == GapSeverity.CRITICAL),
        high_gap_count=sum(1 for g in gaps if g.severity == GapSeverity.HIGH),
        configuration_fingerprint="test",
        analyzer="test",
        analyzer_version="1",
    )
    diagnostics = GapAnalysisDiagnostics(
        input_source_count=1,
        input_evidence_count=1,
        input_ranked_evidence_count=1,
        input_claim_count=0,
        conditions_evaluated=1,
        conditions_passed=0,
        conditions_failed=1,
        conditions_indeterminate=0,
        conditions_unavailable=0,
        gaps_emitted=len(gaps),
        gaps_by_category=_types.MappingProxyType({}),
        gaps_by_severity=_types.MappingProxyType({}),
        configuration_fingerprint="test",
        analyzer="test",
        analyzer_version="1",
    )
    return GapAnalysisResult(
        gaps=gaps,
        quality_diagnostics=quality,
        gap_analysis_diagnostics=diagnostics,
        recommended_status=ResearchStatus.PARTIAL if gaps else ResearchStatus.COMPLETE,
        is_complete=not bool(gaps),
    )


@pytest.mark.synthesis
class TestDeterministicSynthesizerProtocol:
    def test_satisfies_synthesizer_protocol(self) -> None:
        from research_core.protocols.synthesis import Synthesizer

        synth = DeterministicSynthesizer()
        assert isinstance(synth, Synthesizer)

    def test_returns_synthesis_result(self) -> None:
        synth = DeterministicSynthesizer()
        ec = _ec("cl-1", "Revenue increased.")
        inputs = _make_inputs(claims=(ec,))
        result = synth.synthesize(inputs)
        assert isinstance(result, SynthesisResult)

    def test_narrative_non_empty(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        assert result.narrative.strip()

    def test_synthesis_model_set(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        assert result.synthesis_model is not None
        assert "DeterministicSynthesizer" in result.synthesis_model

    def test_no_timestamp_in_output(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        assert result.synthesized_at is None

    def test_no_confidence_score(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        assert result.confidence is None


@pytest.mark.synthesis
class TestDeterministicSynthesizerClaims:
    def test_claim_wording_preserved(self) -> None:
        synth = DeterministicSynthesizer()
        statement = "Revenue increased by $10 million due to market expansion."
        ec = _ec("cl-1", statement, "ev-1")
        result = synth.synthesize(_make_inputs(claims=(ec,)))
        assert statement in result.key_findings

    def test_negation_preserved(self) -> None:
        synth = DeterministicSynthesizer()
        statement = "The treatment did not reduce mortality rates."
        ec = _ec("cl-1", statement, "ev-1")
        result = synth.synthesize(_make_inputs(claims=(ec,)))
        assert statement in result.key_findings

    def test_modality_preserved(self) -> None:
        synth = DeterministicSynthesizer()
        statement = "Demand may increase significantly over the next decade."
        ec = _ec("cl-1", statement, "ev-1")
        result = synth.synthesize(_make_inputs(claims=(ec,)))
        assert statement in result.key_findings

    def test_quantities_preserved(self) -> None:
        synth = DeterministicSynthesizer()
        statement = "Revenue was $100 million."
        ec = _ec("cl-1", statement, "ev-1")
        result = synth.synthesize(_make_inputs(claims=(ec,)))
        assert statement in result.key_findings

    def test_two_distinct_claims_both_in_findings(self) -> None:
        synth = DeterministicSynthesizer()
        ec1 = _ec("cl-1", "Revenue was $10 million.", "ev-1")
        ec2 = _ec("cl-2", "Revenue was $100 million.", "ev-2", "src-2")
        result = synth.synthesize(_make_inputs(claims=(ec1, ec2)))
        assert ec1.claim_text in result.key_findings
        assert ec2.claim_text in result.key_findings

    def test_empty_claims_yields_empty_findings(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        assert result.key_findings == ()


@pytest.mark.synthesis
class TestDeterministicSynthesizerGaps:
    def test_gap_info_in_narrative(self) -> None:
        synth = DeterministicSynthesizer()
        gap = _gap("gap-1", GapSeverity.CRITICAL)
        gap_analysis = _make_gap_analysis((gap,))
        ec = _ec("cl-1", "Climate change impacts biodiversity.", "ev-1")
        inputs = SynthesisInput(
            request_text="What is the impact?",
            sources=(),
            evidence=(),
            claims=(ec,),
            gap_analysis=gap_analysis,  # type: ignore[arg-type]
        )
        result = synth.synthesize(inputs)
        assert "gap" in result.narrative.lower()

    def test_no_unsupported_content(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        forbidden = ["the evidence proves", "the research confirms", "the best strategy"]
        for phrase in forbidden:
            assert phrase.lower() not in result.narrative.lower()


@pytest.mark.synthesis
class TestDeterministicSynthesizerDeterminism:
    def test_identical_inputs_identical_output(self) -> None:
        synth = DeterministicSynthesizer()
        ec = _ec("cl-1", "Climate impact is significant.", "ev-1")
        gap = _gap()
        gap_analysis = _make_gap_analysis((gap,))
        inputs = SynthesisInput(
            request_text="What is the impact?",
            sources=(),
            evidence=(),
            claims=(ec,),
            gap_analysis=gap_analysis,  # type: ignore[arg-type]
        )
        r1 = synth.synthesize(inputs)
        r2 = synth.synthesize(inputs)
        assert r1.narrative == r2.narrative
        assert r1.key_findings == r2.key_findings
        assert r1.synthesis_model == r2.synthesis_model

    def test_repeated_calls_same_instance(self) -> None:
        synth = DeterministicSynthesizer()
        ec = _ec("cl-1", "Test claim.")
        inputs = _make_inputs(claims=(ec,))
        r1 = synth.synthesize(inputs)
        r2 = synth.synthesize(inputs)
        assert r1.narrative == r2.narrative
        assert r1.key_findings == r2.key_findings

    def test_different_instances_same_output(self) -> None:
        ec = _ec("cl-1", "Test claim.")
        inputs = _make_inputs(claims=(ec,))
        r1 = DeterministicSynthesizer().synthesize(inputs)
        r2 = DeterministicSynthesizer().synthesize(inputs)
        assert r1.narrative == r2.narrative


@pytest.mark.synthesis
class TestDeterministicSynthesizerLimitations:
    def test_limitations_text_in_narrative(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        assert "does not imply" in result.narrative.lower()

    def test_no_contradiction_resolution(self) -> None:
        synth = DeterministicSynthesizer()
        ec1 = _ec("cl-1", "Revenue was $10 million.", "ev-1")
        ec2 = _ec("cl-2", "Revenue was $100 million.", "ev-2", "src-2")
        result = synth.synthesize(_make_inputs(claims=(ec1, ec2)))
        assert ec1.claim_text in result.key_findings
        assert ec2.claim_text in result.key_findings


@pytest.mark.synthesis
class TestDeterministicSynthesizerStructured:
    """Tests for RC7 structured synthesis output."""

    def test_has_five_sections(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        assert len(result.sections) == 5

    def test_section_titles_fixed_order(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        titles = [s.title for s in sorted(result.sections, key=lambda s: s.order)]
        assert titles == [
            "Summary",
            "Evidence-Derived Claims",
            "Quality and Coverage",
            "Research Gaps",
            "Limitations",
        ]

    def test_section_ids_deterministic(self) -> None:
        synth = DeterministicSynthesizer()
        r1 = synth.synthesize(_make_inputs())
        r2 = synth.synthesize(_make_inputs())
        assert [s.section_id for s in r1.sections] == [s.section_id for s in r2.sections]

    def test_section_ids_start_with_sec(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        for sec in result.sections:
            assert sec.section_id.startswith("sec-")

    def test_claims_in_section_body(self) -> None:
        synth = DeterministicSynthesizer()
        statement = "Revenue increased by $10 million."
        ec = _ec("cl-1", statement)
        result = synth.synthesize(_make_inputs(claims=(ec,)))
        claims_sec = next(s for s in result.sections if s.title == "Evidence-Derived Claims")
        assert statement in claims_sec.body

    def test_citations_emitted_for_claims(self) -> None:
        synth = DeterministicSynthesizer()
        ec1 = _ec("cl-1", "Revenue was $10 million.", "ev-1")
        ec2 = _ec("cl-2", "Costs rose 5%.", "ev-2")
        result = synth.synthesize(_make_inputs(claims=(ec1, ec2)))
        assert len(result.citations) == 2

    def test_citation_ids_start_with_cit(self) -> None:
        synth = DeterministicSynthesizer()
        ec = _ec("cl-1", "Revenue increased.")
        result = synth.synthesize(_make_inputs(claims=(ec,)))
        for cit in result.citations:
            assert cit.citation_id.startswith("cit-")

    def test_citation_ids_cross_process_stable(self) -> None:
        # Same inputs always yield same citation IDs
        ec = _ec("cl-1", "Revenue increased.")
        r1 = DeterministicSynthesizer().synthesize(_make_inputs(claims=(ec,)))
        r2 = DeterministicSynthesizer().synthesize(_make_inputs(claims=(ec,)))
        assert r1.citations[0].citation_id == r2.citations[0].citation_id

    def test_synthesis_diagnostics_present(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        assert result.synthesis_diagnostics is not None
        diag = result.synthesis_diagnostics
        assert diag.synthesizer == "DeterministicSynthesizer"
        assert diag.sections_emitted == 5

    def test_synthesis_status_complete(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        from research_core.synthesis.contracts import SynthesisStatus
        assert result.synthesis_status == SynthesisStatus.COMPLETE

    def test_limitations_section_body_non_empty(self) -> None:
        synth = DeterministicSynthesizer()
        result = synth.synthesize(_make_inputs())
        lim_sec = next(s for s in result.sections if s.title == "Limitations")
        assert lim_sec.body.strip()
