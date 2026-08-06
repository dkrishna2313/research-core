"""
Purity tests for MarkdownRenderer.

Purity: render() must never mutate the ResearchResult or any of its fields.
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


def _make_result() -> ResearchResult:
    src = Source(source_id="src-1", source_type=SourceType.KNOWLEDGE, title="Source One")
    prov = Provenance(source_id="src-1", source_type=SourceType.KNOWLEDGE, retrieved_at=FIXED_TS)
    ev = EvidenceItem(
        evidence_id="ev-1",
        content="Climate change is affecting ecosystems.",
        source_id="src-1",
        provenance=prov,
        quality=EvidenceQuality(relevance=0.85, authority=0.75),
    )
    cl = Claim(
        claim_id="cl-1",
        statement="Climate change is significant.",
        supporting_evidence_ids=("ev-1",),
    )
    gap = ResearchGap(
        gap_id="gap-1",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        description="Not enough primary sources.",
        severity=GapSeverity.MEDIUM,
        status=GapStatus.OPEN,
    )
    syn = SynthesisResult(
        narrative="The research produced 1 claim from 1 evidence item.",
        key_findings=("Climate change is significant.",),
        synthesis_model="DeterministicSynthesizer/1.0",
    )
    trace = ResearchTrace(
        events=(
            TraceEvent(
                event_id="evt-0001",
                stage=TraceStage.INIT,
                status=TraceEventStatus.COMPLETED,
                message="Initialized.",
                occurred_at=FIXED_TS,
            ),
        )
    )
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
        quality=QualityDiagnostics(relevance=QualityDimension(score=0.85)),
        trace=trace,
        completed_at=FIXED_TS,
    )


@pytest.mark.renderers
class TestMarkdownRendererPurity:
    def test_result_object_not_mutated(self) -> None:
        renderer = MarkdownRenderer()
        result = _make_result()
        result_id = id(result)
        renderer.render(result)
        # Same object identity (frozen dataclass prevents mutation anyway)
        assert id(result) == result_id

    def test_result_request_unchanged(self) -> None:
        renderer = MarkdownRenderer()
        result = _make_result()
        original_question = result.request.question
        renderer.render(result)
        assert result.request.question == original_question

    def test_result_sources_unchanged(self) -> None:
        renderer = MarkdownRenderer()
        result = _make_result()
        original_src_ids = tuple(s.source_id for s in result.sources)
        renderer.render(result)
        assert tuple(s.source_id for s in result.sources) == original_src_ids

    def test_result_evidence_unchanged(self) -> None:
        renderer = MarkdownRenderer()
        result = _make_result()
        original_ev_ids = tuple(e.evidence_id for e in result.evidence)
        renderer.render(result)
        assert tuple(e.evidence_id for e in result.evidence) == original_ev_ids

    def test_result_claims_unchanged(self) -> None:
        renderer = MarkdownRenderer()
        result = _make_result()
        original_cl_ids = tuple(c.claim_id for c in result.claims)
        renderer.render(result)
        assert tuple(c.claim_id for c in result.claims) == original_cl_ids

    def test_result_synthesis_unchanged(self) -> None:
        renderer = MarkdownRenderer()
        result = _make_result()
        assert result.synthesis is not None
        original_narrative = result.synthesis.narrative
        renderer.render(result)
        assert result.synthesis is not None
        assert result.synthesis.narrative == original_narrative

    def test_result_gaps_unchanged(self) -> None:
        renderer = MarkdownRenderer()
        result = _make_result()
        original_gap_ids = tuple(g.gap_id for g in result.gaps)
        renderer.render(result)
        assert tuple(g.gap_id for g in result.gaps) == original_gap_ids

    def test_result_trace_unchanged(self) -> None:
        renderer = MarkdownRenderer()
        result = _make_result()
        assert result.trace is not None
        original_evt_count = len(result.trace.events)
        renderer.render(result)
        assert result.trace is not None
        assert len(result.trace.events) == original_evt_count

    def test_result_status_unchanged(self) -> None:
        renderer = MarkdownRenderer()
        result = _make_result()
        original_status = result.status
        renderer.render(result)
        assert result.status == original_status

    def test_render_does_not_raise_on_minimal_result(self) -> None:
        renderer = MarkdownRenderer()
        src = Source(source_id="s", source_type=SourceType.KNOWLEDGE)
        ev = EvidenceItem(
            evidence_id="e",
            content="test",
            source_id="s",
            provenance=Provenance(
                source_id="s", source_type=SourceType.KNOWLEDGE, retrieved_at=FIXED_TS
            ),
            quality=EvidenceQuality(),
        )
        result = ResearchResult(
            request=ResearchRequest(question="?"),
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
        assert md

    def test_render_output_is_deterministic(self) -> None:
        renderer = MarkdownRenderer()
        result = _make_result()
        outputs = [renderer.render(result) for _ in range(5)]
        assert all(o == outputs[0] for o in outputs[1:])

    def test_separate_renderer_instances_identical_output(self) -> None:
        result = _make_result()
        md1 = MarkdownRenderer().render(result)
        md2 = MarkdownRenderer().render(result)
        assert md1 == md2
