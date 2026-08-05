"""
Tests for MarkdownRenderer.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from research_core.contracts.claims import Claim
from research_core.contracts.common import SourceType
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import GapSeverity, GapStatus, GapType, ResearchGap
from research_core.contracts.quality import QualityDiagnostics, QualityDimension
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import ResearchResult, ResearchStatus, SynthesisResult
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.contracts.trace import ResearchTrace, TraceEvent, TraceEventStatus, TraceStage
from research_core.renderers.markdown import MarkdownRenderer

FIXED_TS = datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)


def _prov(source_id: str) -> Provenance:
    return Provenance(
        source_id=source_id,
        source_type=SourceType.KNOWLEDGE,
        retrieved_at=FIXED_TS,
    )


def _src(source_id: str = "src-1", title: str = "Test Source") -> Source:
    return Source(
        source_id=source_id,
        source_type=SourceType.KNOWLEDGE,
        title=title,
    )


def _ev(evidence_id: str = "ev-1", source_id: str = "src-1") -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        content="Climate change significantly affects biodiversity.",
        source_id=source_id,
        provenance=_prov(source_id),
        quality=EvidenceQuality(relevance=0.8, authority=0.7),
    )


def _claim(claim_id: str = "cl-1", statement: str = "Climate change is significant.") -> Claim:
    return Claim(
        claim_id=claim_id,
        statement=statement,
        supporting_evidence_ids=("ev-1",),
    )


def _gap(gap_id: str = "gap-1") -> ResearchGap:
    return ResearchGap(
        gap_id=gap_id,
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        description="Insufficient evidence coverage.",
        severity=GapSeverity.MEDIUM,
        status=GapStatus.OPEN,
    )


def _trace_event(event_id: str = "evt-0001") -> TraceEvent:
    return TraceEvent(
        event_id=event_id,
        stage=TraceStage.INIT,
        status=TraceEventStatus.COMPLETED,
        message="Initialized.",
        occurred_at=FIXED_TS,
    )


def _complete_result() -> ResearchResult:
    src = _src()
    ev = _ev()
    cl = _claim()
    gap = _gap()
    syn = SynthesisResult(
        narrative="The research produced 1 claim from 1 evidence item.",
        key_findings=("Climate change is significant.",),
        synthesis_model="DeterministicSynthesizer/1.0",
    )
    trace = ResearchTrace(events=(_trace_event(),))
    return ResearchResult(
        request=ResearchRequest(question="What is the impact?"),
        status=ResearchStatus.COMPLETE,
        sources=(src,),
        evidence=(ev,),
        claims=(cl,),
        contradictions=(),
        gaps=(gap,),
        open_questions=(),
        synthesis=syn,
        quality=QualityDiagnostics(relevance=QualityDimension(score=0.8)),
        trace=trace,
        completed_at=FIXED_TS,
    )


def _partial_result_no_synthesis() -> ResearchResult:
    src = _src()
    ev = _ev()
    cl = _claim()
    gap = _gap()
    trace = ResearchTrace(
        events=(
            _trace_event("evt-0001"),
            TraceEvent(
                event_id="evt-0002",
                stage=TraceStage.SYNTHESIS,
                status=TraceEventStatus.FAILED,
                message="Synthesis failed.",
                occurred_at=FIXED_TS,
            ),
        )
    )
    return ResearchResult(
        request=ResearchRequest(question="What is the impact?"),
        status=ResearchStatus.PARTIAL,
        sources=(src,),
        evidence=(ev,),
        claims=(cl,),
        contradictions=(),
        gaps=(gap,),
        open_questions=(),
        synthesis=None,
        quality=QualityDiagnostics(relevance=QualityDimension(score=0.8)),
        trace=trace,
        completed_at=FIXED_TS,
    )


@pytest.mark.renderers
class TestMarkdownRendererBasic:
    def test_render_returns_string(self) -> None:
        renderer = MarkdownRenderer()
        result = _complete_result()
        md = renderer.render(result)
        assert isinstance(md, str)

    def test_render_ends_with_newline(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert md.endswith("\n")

    def test_render_ends_with_exactly_one_newline(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert not md.endswith("\n\n")

    def test_no_trailing_whitespace_per_line(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        for line in md.splitlines():
            assert line == line.rstrip(), f"Trailing whitespace on line: {line!r}"

    def test_contains_research_question(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert "What is the impact?" in md

    def test_contains_status(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert "complete" in md.lower()

    def test_contains_source_ids(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert "src-1" in md

    def test_contains_evidence_ids(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert "ev-1" in md

    def test_contains_claim_ids(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert "cl-1" in md

    def test_contains_gap_info(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert "gap-1" in md

    def test_contains_synthesis_narrative(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert "The research produced 1 claim" in md


@pytest.mark.renderers
class TestMarkdownRendererPartial:
    def test_partial_notice_present(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_partial_result_no_synthesis())
        assert "partial" in md.lower()

    def test_synthesis_not_available_message(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_partial_result_no_synthesis())
        assert "synthesis" in md.lower()
        assert "not available" in md.lower() or "not performed" in md.lower()


@pytest.mark.renderers
class TestMarkdownRendererQuality:
    def test_quality_dimensions_rendered(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert "relevance" in md.lower()

    def test_none_quality_renders_unavailable(self) -> None:
        renderer = MarkdownRenderer()
        result = _complete_result()
        # authority is None in the fixture
        md = renderer.render(result)
        assert "Unavailable" in md

    def test_zero_score_renders_as_zero(self) -> None:
        renderer = MarkdownRenderer()
        src = _src()
        ev = _ev()
        cl = _claim()
        result = ResearchResult(
            request=ResearchRequest(question="test"),
            status=ResearchStatus.COMPLETE,
            sources=(src,),
            evidence=(ev,),
            claims=(cl,),
            contradictions=(),
            gaps=(),
            open_questions=(),
            quality=QualityDiagnostics(relevance=QualityDimension(score=0.0)),
            completed_at=FIXED_TS,
        )
        md = renderer.render(result)
        assert "0.000" in md


@pytest.mark.renderers
class TestMarkdownRendererEdgeCases:
    def test_no_claims(self) -> None:
        renderer = MarkdownRenderer()
        src = _src()
        ev = _ev()
        result = ResearchResult(
            request=ResearchRequest(question="test"),
            status=ResearchStatus.PARTIAL,
            sources=(src,),
            evidence=(ev,),
            claims=(),
            contradictions=(),
            gaps=(),
            open_questions=(),
            completed_at=FIXED_TS,
        )
        md = renderer.render(result)
        assert "No claims" in md

    def test_no_gaps(self) -> None:
        renderer = MarkdownRenderer()
        result = ResearchResult(
            request=ResearchRequest(question="test"),
            status=ResearchStatus.COMPLETE,
            sources=(_src(),),
            evidence=(_ev(),),
            claims=(_claim(),),
            contradictions=(),
            gaps=(),
            open_questions=(),
            completed_at=FIXED_TS,
        )
        md = renderer.render(result)
        assert "No research gaps" in md

    def test_no_trace(self) -> None:
        renderer = MarkdownRenderer()
        src = _src()
        ev = _ev()
        result = ResearchResult(
            request=ResearchRequest(question="test"),
            status=ResearchStatus.COMPLETE,
            sources=(src,),
            evidence=(ev,),
            claims=(),
            contradictions=(),
            gaps=(),
            open_questions=(),
            trace=None,
            completed_at=FIXED_TS,
        )
        md = renderer.render(result)
        assert "No trace events" in md

    def test_source_with_url(self) -> None:
        renderer = MarkdownRenderer()
        src = Source(
            source_id="src-url",
            source_type=SourceType.WEB,
            title="Web Source",
            url="https://example.com/article",
        )
        ev = EvidenceItem(
            evidence_id="ev-1",
            content="Test content.",
            source_id="src-url",
            provenance=Provenance(
                source_id="src-url",
                source_type=SourceType.WEB,
                retrieved_at=FIXED_TS,
                url="https://example.com/article",
            ),
            quality=EvidenceQuality(),
        )
        result = ResearchResult(
            request=ResearchRequest(question="test"),
            status=ResearchStatus.COMPLETE,
            sources=(src,),
            evidence=(ev,),
            claims=(),
            contradictions=(),
            gaps=(),
            open_questions=(),
            completed_at=FIXED_TS,
        )
        md = renderer.render(result)
        assert "https://example.com/article" in md

    def test_repeated_render_identical(self) -> None:
        renderer = MarkdownRenderer()
        result = _complete_result()
        md1 = renderer.render(result)
        md2 = renderer.render(result)
        assert md1 == md2

    def test_gap_severity_rendered(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert "MEDIUM" in md

    def test_no_python_reprs(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        assert "MappingProxyType" not in md
        assert "<research_core." not in md
        assert "object at 0x" not in md
