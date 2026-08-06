"""
RC7 regression tests for structured synthesis rendering.

Verifies that MarkdownRenderer correctly handles:
  - Structured synthesis sections (not legacy narrative)
  - Summary section body in Executive Summary
  - Non-summary sections in Synthesis section
  - Citations block
  - RC6 quality diagnostics from gap_analysis
  - No duplicate quality table when RC6 is used
"""

from __future__ import annotations

import types

import pytest

from research_core.analysis.contracts import (
    CoverageDiagnostics,
    DiagnosticStatus,
    DistributionDiagnostics,
    EvidenceConditionDiagnostics,
    GapAnalysisDiagnostics,
    GapAnalysisResult,
    QualityDiagnosticsResult,
)
from research_core.contracts.common import SourceType
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import ResearchResult, ResearchStatus, SynthesisResult
from research_core.contracts.sources import Provenance, Source
from research_core.renderers.markdown import MarkdownRenderer
from research_core.synthesis.contracts import (
    SynthesisCitation,
    SynthesisDiagnostics,
    SynthesisSection,
    SynthesisStatus,
)

FIXED_TS_STR = "2024-01-15T00:00:00+00:00"


def _prov() -> Provenance:
    from datetime import UTC, datetime
    return Provenance(
        source_id="src-1",
        source_type=SourceType.KNOWLEDGE,
        retrieved_at=datetime(2024, 1, 15, tzinfo=UTC),
    )


def _src(source_id: str = "src-1") -> Source:
    return Source(source_id=source_id, source_type=SourceType.KNOWLEDGE, title="Test Source")


def _minimal_quality() -> QualityDiagnosticsResult:
    return QualityDiagnosticsResult(
        overall_status=DiagnosticStatus.PASS,
        overall_score=None,
        dimensions=(),
        coverage=CoverageDiagnostics(
            source_count=1,
            evidence_count=1,
            ranked_evidence_count=1,
            claim_count=0,
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
            evidence_per_source=types.MappingProxyType({}),
            evidence_per_provider=types.MappingProxyType({}),
        ),
        evidence_conditions=EvidenceConditionDiagnostics(
            truncated_evidence_count=0,
            duplicate_evidence_count=0,
            near_duplicate_evidence_count=0,
            missing_retrieval_score_count=0,
            missing_retrieval_rank_count=0,
            invalid_lineage_count=0,
        ),
        gap_count=0,
        critical_gap_count=0,
        high_gap_count=0,
        configuration_fingerprint="test",
        analyzer="DeterministicGapAnalyzer",
        analyzer_version="1",
    )


def _minimal_gap_analysis() -> GapAnalysisResult:
    diag = GapAnalysisDiagnostics(
        input_source_count=1,
        input_evidence_count=1,
        input_ranked_evidence_count=1,
        input_claim_count=0,
        conditions_evaluated=1,
        conditions_passed=1,
        conditions_failed=0,
        conditions_indeterminate=0,
        conditions_unavailable=0,
        gaps_emitted=0,
        gaps_by_category=types.MappingProxyType({}),
        gaps_by_severity=types.MappingProxyType({}),
        configuration_fingerprint="test",
        analyzer="DeterministicGapAnalyzer",
        analyzer_version="1",
    )
    return GapAnalysisResult(
        gaps=(),
        quality_diagnostics=_minimal_quality(),
        gap_analysis_diagnostics=diag,
        recommended_status=ResearchStatus.COMPLETE,
        is_complete=True,
    )


def _make_synthesis_sections() -> tuple[SynthesisSection, ...]:
    return (
        SynthesisSection(
            section_id="sec-summary",
            title="Summary",
            body="This is the structured summary body.",
            order=0,
        ),
        SynthesisSection(
            section_id="sec-claims",
            title="Evidence-Derived Claims",
            body="1. Revenue increased by $10 million.",
            order=1,
        ),
        SynthesisSection(
            section_id="sec-quality",
            title="Quality and Coverage",
            body="Quality: pass.",
            order=2,
        ),
        SynthesisSection(
            section_id="sec-gaps",
            title="Research Gaps",
            body="No critical gaps identified.",
            order=3,
        ),
        SynthesisSection(
            section_id="sec-limits",
            title="Limitations",
            body="Correlation does not imply causation.",
            order=4,
        ),
    )


def _make_citations() -> tuple[SynthesisCitation, ...]:
    return (
        SynthesisCitation(
            citation_id="cit-aabbccddee1122334455",
            claim_id="cl-1",
            evidence_id="ev-1",
            source_id="src-1",
            section_id="sec-claims",
            label="[1]",
        ),
    )


def _make_synthesis_diag() -> SynthesisDiagnostics:
    return SynthesisDiagnostics(
        input_source_count=1,
        input_evidence_count=1,
        input_claim_count=1,
        input_gap_count=0,
        claims_used=1,
        claims_unused=0,
        evidence_used=1,
        evidence_unused=0,
        sections_emitted=5,
        citations_emitted=1,
        configuration_fingerprint="cfg-abc",
        synthesizer="DeterministicSynthesizer",
        synthesizer_version="1",
    )


def _structured_result(with_gap_analysis: bool = False) -> ResearchResult:
    syn = SynthesisResult(
        narrative="Legacy narrative (should not appear in structured render).",
        key_findings=("This should not appear.",),
        synthesis_model="DeterministicSynthesizer/1.0",
        sections=_make_synthesis_sections(),
        citations=_make_citations(),
        synthesis_diagnostics=_make_synthesis_diag(),
        synthesis_status=SynthesisStatus.COMPLETE,
    )
    return ResearchResult(
        request=ResearchRequest(question="What is the impact?"),
        status=ResearchStatus.COMPLETE,
        sources=(_src(),),
        evidence=(),
        claims=(),
        contradictions=(),
        gaps=(),
        open_questions=(),
        synthesis=syn,
        gap_analysis=_minimal_gap_analysis() if with_gap_analysis else None,
    )


@pytest.mark.renderers
class TestStructuredSynthesisRendering:
    def test_summary_section_body_in_executive_summary(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result())
        assert "This is the structured summary body." in md

    def test_legacy_narrative_not_in_output(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result())
        assert "Legacy narrative (should not appear in structured render)." not in md

    def test_legacy_key_findings_not_in_output(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result())
        assert "This should not appear." not in md

    def test_evidence_derived_claims_section_present(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result())
        assert "Evidence-Derived Claims" in md
        assert "Revenue increased by $10 million." in md

    def test_research_gaps_section_present(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result())
        assert "Research Gaps" in md
        assert "No critical gaps identified." in md

    def test_limitations_section_present(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result())
        assert "Limitations" in md
        assert "Correlation does not imply causation." in md

    def test_citations_block_present(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result())
        assert "Citations" in md
        assert "cit-aabbccddee1122334455" in md or "[1]" in md

    def test_citation_references_claim_and_evidence_ids(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result())
        assert "cl-1" in md
        assert "ev-1" in md

    def test_no_trailing_whitespace(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result())
        for ln in md.splitlines():
            assert ln == ln.rstrip(), f"Trailing whitespace: {ln!r}"

    def test_ends_with_single_newline(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result())
        assert md.endswith("\n")
        assert not md.endswith("\n\n")


@pytest.mark.renderers
class TestRC6QualityRendering:
    def test_rc6_quality_status_rendered(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result(with_gap_analysis=True))
        assert "pass" in md.lower() or "PASS" in md

    def test_rc6_coverage_info_rendered(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result(with_gap_analysis=True))
        assert "source" in md.lower()

    def test_legacy_composite_score_not_rendered_when_rc6(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result(with_gap_analysis=True))
        assert "Composite Score" not in md

    def test_quality_unavailable_message_absent_when_rc6(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_structured_result(with_gap_analysis=True))
        assert "Quality diagnostics unavailable" not in md

    def test_quality_unavailable_when_neither(self) -> None:
        renderer = MarkdownRenderer()
        result = _structured_result(with_gap_analysis=False)
        md = renderer.render(result)
        assert "unavailable" in md.lower()
