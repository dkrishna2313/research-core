"""
Snapshot tests for MarkdownRenderer.

Compares rendered output against committed snapshot files.
Re-generate snapshots: REGENERATE_SNAPSHOTS=1 pytest tests/renderers/test_snapshot.py
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from research_core.contracts.claims import Claim, ClaimType
from research_core.contracts.common import SourceType
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import (
    GapSeverity,
    GapStatus,
    GapType,
    OpenQuestion,
    QuestionPriority,
    ResearchGap,
)
from research_core.contracts.quality import QualityDiagnostics, QualityDimension
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import ResearchResult, ResearchStatus, SynthesisResult
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.contracts.trace import ResearchTrace, TraceEvent, TraceEventStatus, TraceStage
from research_core.renderers.markdown import MarkdownRenderer

_SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
_REGENERATE = os.environ.get("REGENERATE_SNAPSHOTS", "").strip() not in ("", "0")

FIXED_TS = datetime(2024, 3, 1, 12, 0, 0, tzinfo=UTC)


def _complete_result() -> ResearchResult:
    src1 = Source(
        source_id="src-know-01",
        source_type=SourceType.KNOWLEDGE,
        title="IPCC Sixth Assessment Report",
        publisher="IPCC",
    )
    src2 = Source(
        source_id="src-web-01",
        source_type=SourceType.WEB,
        title="Climate Biodiversity Impact",
        url="https://example.org/climate-biodiversity",
    )
    prov1 = Provenance(
        source_id="src-know-01",
        source_type=SourceType.KNOWLEDGE,
        retrieved_at=FIXED_TS,
    )
    prov2 = Provenance(
        source_id="src-web-01",
        source_type=SourceType.WEB,
        retrieved_at=FIXED_TS,
        url="https://example.org/climate-biodiversity",
    )
    ev1 = EvidenceItem(
        evidence_id="ev-001",
        content="Global average temperatures have risen by 1.1°C since pre-industrial times.",
        source_id="src-know-01",
        provenance=prov1,
        quality=EvidenceQuality(relevance=0.95, authority=0.90, recency=0.80),
    )
    ev2 = EvidenceItem(
        evidence_id="ev-002",
        content="Approximately 1 million species are currently at risk of extinction.",
        source_id="src-web-01",
        provenance=prov2,
        quality=EvidenceQuality(relevance=0.85, authority=0.70),
    )
    cl1 = Claim(
        claim_id="cl-001",
        statement="Global temperatures have risen 1.1°C since pre-industrial times.",
        claim_type=ClaimType.FACTUAL,
        supporting_evidence_ids=("ev-001",),
    )
    cl2 = Claim(
        claim_id="cl-002",
        statement="Approximately 1 million species face extinction risk.",
        claim_type=ClaimType.FACTUAL,
        supporting_evidence_ids=("ev-002",),
    )
    gap = ResearchGap(
        gap_id="gap-001",
        gap_type=GapType.MISSING_DIMENSION,
        description="Evidence does not cover projections beyond 2050.",
        severity=GapSeverity.HIGH,
        status=GapStatus.OPEN,
        recommended_action="Retrieve sources covering post-2050 projections.",
    )
    oq = OpenQuestion(
        question="What are the projected extinction rates after 2100?",
        priority=QuestionPriority.HIGH,
        reason="Current evidence does not cover long-term projections.",
    )
    syn = SynthesisResult(
        narrative=(
            "The research retrieved 2 evidence item(s) from 2 source(s), "
            "yielding 2 claim(s). "
            "1 research gap(s) were identified. "
            "This synthesis does not imply verification, corroboration, or truth inference."
        ),
        key_findings=(
            "Global temperatures have risen 1.1°C since pre-industrial times.",
            "Approximately 1 million species face extinction risk.",
        ),
        synthesis_model="DeterministicSynthesizer/1.0",
    )
    trace = ResearchTrace(
        events=(
            TraceEvent(
                event_id="evt-0001",
                stage=TraceStage.INIT,
                status=TraceEventStatus.COMPLETED,
                message="Research engine starting.",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0002",
                stage=TraceStage.PROFILE_RESOLUTION,
                status=TraceEventStatus.SKIPPED,
                message="No profiles specified; profile resolution skipped.",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0003",
                stage=TraceStage.RETRIEVAL,
                status=TraceEventStatus.COMPLETED,
                message="Knowledge retrieval: 1 item(s) from 1 source(s).",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0004",
                stage=TraceStage.RETRIEVAL,
                status=TraceEventStatus.COMPLETED,
                message="Web retrieval: 1 item(s) from 1 source(s).",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0005",
                stage=TraceStage.EXTRACTION,
                status=TraceEventStatus.COMPLETED,
                message="Claim extraction: 2 claim(s) extracted.",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0006",
                stage=TraceStage.CONTRADICTION_DETECTION,
                status=TraceEventStatus.SKIPPED,
                message="Contradiction detection skipped (no detector configured).",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0007",
                stage=TraceStage.GAP_ANALYSIS,
                status=TraceEventStatus.COMPLETED,
                message="Gap analysis: 1 gap(s), 1 open question(s).",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0008",
                stage=TraceStage.SYNTHESIS,
                status=TraceEventStatus.COMPLETED,
                message="Synthesis completed.",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0009",
                stage=TraceStage.FINALIZATION,
                status=TraceEventStatus.COMPLETED,
                message=(
                    "Research finalized. Status: complete. "
                    "Sources: 2, evidence: 2, claims: 2, gaps: 1."
                ),
                occurred_at=FIXED_TS,
            ),
        )
    )
    return ResearchResult(
        request=ResearchRequest(question="What is the impact of climate change on biodiversity?"),
        status=ResearchStatus.COMPLETE,
        sources=(src1, src2),
        evidence=(ev1, ev2),
        claims=(cl1, cl2),
        contradictions=(),
        gaps=(gap,),
        open_questions=(oq,),
        synthesis=syn,
        quality=QualityDiagnostics(
            relevance=QualityDimension(score=0.90),
            authority=QualityDimension(score=0.80),
            recency=QualityDimension(score=0.80),
        ),
        trace=trace,
        completed_at=FIXED_TS,
    )


def _partial_synthesis_failure() -> ResearchResult:
    src = Source(
        source_id="src-know-01",
        source_type=SourceType.KNOWLEDGE,
        title="Energy Policy Review",
    )
    prov = Provenance(
        source_id="src-know-01",
        source_type=SourceType.KNOWLEDGE,
        retrieved_at=FIXED_TS,
    )
    ev = EvidenceItem(
        evidence_id="ev-001",
        content="Renewable energy capacity grew 12% in 2023.",
        source_id="src-know-01",
        provenance=prov,
        quality=EvidenceQuality(relevance=0.80, authority=0.65),
    )
    cl = Claim(
        claim_id="cl-001",
        statement="Renewable energy capacity grew 12% in 2023.",
        claim_type=ClaimType.FACTUAL,
        supporting_evidence_ids=("ev-001",),
    )
    gap = ResearchGap(
        gap_id="gap-001",
        gap_type=GapType.INSUFFICIENT_COVERAGE,
        description="Only one source available; corroboration not possible.",
        severity=GapSeverity.MEDIUM,
        status=GapStatus.OPEN,
    )
    trace = ResearchTrace(
        events=(
            TraceEvent(
                event_id="evt-0001",
                stage=TraceStage.INIT,
                status=TraceEventStatus.COMPLETED,
                message="Research engine starting.",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0002",
                stage=TraceStage.PROFILE_RESOLUTION,
                status=TraceEventStatus.SKIPPED,
                message="No profiles specified; profile resolution skipped.",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0003",
                stage=TraceStage.RETRIEVAL,
                status=TraceEventStatus.COMPLETED,
                message="Knowledge retrieval: 1 item(s) from 1 source(s).",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0004",
                stage=TraceStage.RETRIEVAL,
                status=TraceEventStatus.SKIPPED,
                message="Web retrieval skipped (not requested).",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0005",
                stage=TraceStage.EXTRACTION,
                status=TraceEventStatus.COMPLETED,
                message="Claim extraction: 1 claim(s) extracted.",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0006",
                stage=TraceStage.CONTRADICTION_DETECTION,
                status=TraceEventStatus.SKIPPED,
                message="Contradiction detection skipped (no detector configured).",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0007",
                stage=TraceStage.GAP_ANALYSIS,
                status=TraceEventStatus.COMPLETED,
                message="Gap analysis: 1 gap(s), 0 open question(s).",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0008",
                stage=TraceStage.SYNTHESIS,
                status=TraceEventStatus.FAILED,
                message="Synthesis failed; result will be partial.",
                occurred_at=FIXED_TS,
            ),
            TraceEvent(
                event_id="evt-0009",
                stage=TraceStage.FINALIZATION,
                status=TraceEventStatus.COMPLETED,
                message=(
                    "Research finalized. Status: partial. "
                    "Sources: 1, evidence: 1, claims: 1, gaps: 1."
                ),
                occurred_at=FIXED_TS,
            ),
        )
    )
    return ResearchResult(
        request=ResearchRequest(question="What is the current state of renewable energy?"),
        status=ResearchStatus.PARTIAL,
        sources=(src,),
        evidence=(ev,),
        claims=(cl,),
        contradictions=(),
        gaps=(gap,),
        open_questions=(),
        synthesis=None,
        quality=QualityDiagnostics(
            relevance=QualityDimension(score=0.80),
            authority=QualityDimension(score=0.65),
        ),
        trace=trace,
        completed_at=FIXED_TS,
    )


def _snapshot_path(name: str) -> Path:
    return _SNAPSHOTS_DIR / name


def _assert_or_generate(name: str, actual: str) -> None:
    path = _snapshot_path(name)
    if _REGENERATE:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        return
    if not path.exists():
        pytest.fail(
            f"Snapshot file not found: {path}\n"
            f"Run with REGENERATE_SNAPSHOTS=1 to create it."
        )
    expected = path.read_text(encoding="utf-8")
    assert actual == expected, (
        f"Rendered output does not match snapshot {name}.\n"
        f"Run with REGENERATE_SNAPSHOTS=1 to update."
    )


@pytest.mark.renderers
class TestMarkdownSnapshots:
    def test_complete_result_snapshot(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_complete_result())
        _assert_or_generate("complete_result.md", md)

    def test_partial_synthesis_failure_snapshot(self) -> None:
        renderer = MarkdownRenderer()
        md = renderer.render(_partial_synthesis_failure())
        _assert_or_generate("partial_synthesis_failure.md", md)
