"""
Shared test fixtures and factory helpers.

All factories accept keyword overrides so individual test cases can
vary a single field without reconstructing the entire object.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from research_core.contracts.claims import Claim
from research_core.contracts.contradictions import (
    Contradiction,
    ContradictionType,
)
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import GapType, OpenQuestion, ResearchGap
from research_core.contracts.quality import QualityDiagnostics
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import ResearchResult, ResearchStatus, SynthesisResult
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.contracts.trace import TraceEvent, TraceEventStatus, TraceStage

FIXED_TS = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)


def make_source(
    source_id: str = "src-1",
    **kwargs: Any,
) -> Source:
    from research_core.contracts.common import SourceType

    defaults: dict[str, Any] = {
        "source_id": source_id,
        "source_type": SourceType.KNOWLEDGE,
        "title": "Test Source",
    }
    defaults.update(kwargs)
    return Source(**defaults)


def make_provenance(
    source_id: str = "src-1",
    **kwargs: Any,
) -> Provenance:
    from research_core.contracts.common import SourceType

    defaults: dict[str, Any] = {
        "source_id": source_id,
        "source_type": SourceType.KNOWLEDGE,
        "retrieved_at": FIXED_TS,
    }
    defaults.update(kwargs)
    return Provenance(**defaults)


def make_evidence_quality(**kwargs: Any) -> EvidenceQuality:
    return EvidenceQuality(**kwargs)


def make_evidence_item(
    evidence_id: str = "ev-1",
    source_id: str = "src-1",
    **kwargs: Any,
) -> EvidenceItem:
    defaults: dict[str, Any] = {
        "evidence_id": evidence_id,
        "content": "Test evidence content.",
        "source_id": source_id,
        "provenance": make_provenance(source_id=source_id),
        "quality": make_evidence_quality(),
    }
    defaults.update(kwargs)
    return EvidenceItem(**defaults)


def make_claim(
    claim_id: str = "cl-1",
    **kwargs: Any,
) -> Claim:
    defaults: dict[str, Any] = {
        "claim_id": claim_id,
        "statement": "Test claim statement.",
    }
    defaults.update(kwargs)
    return Claim(**defaults)


def make_contradiction(
    contradiction_id: str = "con-1",
    claim_ids: tuple[str, ...] = ("cl-1", "cl-2"),
    **kwargs: Any,
) -> Contradiction:
    defaults: dict[str, Any] = {
        "contradiction_id": contradiction_id,
        "contradiction_type": ContradictionType.NUMERIC,
        "description": "Test contradiction.",
        "claim_ids": claim_ids,
    }
    defaults.update(kwargs)
    return Contradiction(**defaults)


def make_gap(
    gap_id: str = "gap-1",
    **kwargs: Any,
) -> ResearchGap:
    defaults: dict[str, Any] = {
        "gap_id": gap_id,
        "gap_type": GapType.NO_EVIDENCE,
        "description": "Test gap.",
    }
    defaults.update(kwargs)
    return ResearchGap(**defaults)


def make_open_question(question: str = "What is the scope?", **kwargs: Any) -> OpenQuestion:
    return OpenQuestion(question=question, **kwargs)


def make_quality_diagnostics(**kwargs: Any) -> QualityDiagnostics:
    return QualityDiagnostics(**kwargs)


def make_trace_event(
    event_id: str = "evt-1",
    **kwargs: Any,
) -> TraceEvent:
    defaults: dict[str, Any] = {
        "event_id": event_id,
        "stage": TraceStage.INIT,
        "status": TraceEventStatus.COMPLETED,
        "message": "Initialized.",
        "occurred_at": FIXED_TS,
    }
    defaults.update(kwargs)
    return TraceEvent(**defaults)


def make_research_request(**kwargs: Any) -> ResearchRequest:
    defaults: dict[str, Any] = {
        "question": "What is the impact of climate change on biodiversity?",
    }
    defaults.update(kwargs)
    return ResearchRequest(**defaults)


def make_synthesis_result(**kwargs: Any) -> SynthesisResult:
    defaults: dict[str, Any] = {
        "narrative": "Based on the evidence, the impact is significant.",
        "key_findings": ("Finding A.", "Finding B."),
        "synthesized_at": FIXED_TS,
    }
    defaults.update(kwargs)
    return SynthesisResult(**defaults)


def make_minimal_result(**kwargs: Any) -> ResearchResult:
    """A ResearchResult with no evidence, claims, or contradictions."""
    source = make_source()
    defaults: dict[str, Any] = {
        "request": make_research_request(),
        "status": ResearchStatus.COMPLETE,
        "sources": (source,),
        "evidence": (),
        "claims": (),
        "contradictions": (),
        "gaps": (),
        "open_questions": (),
        "completed_at": FIXED_TS,
    }
    defaults.update(kwargs)
    return ResearchResult(**defaults)


def make_full_result(**kwargs: Any) -> ResearchResult:
    """A ResearchResult with linked sources, evidence, claims, and gaps."""
    source = make_source(source_id="src-1")
    ev = make_evidence_item(evidence_id="ev-1", source_id="src-1")
    cl = make_claim(
        claim_id="cl-1",
        supporting_evidence_ids=("ev-1",),
    )
    gap = make_gap(gap_id="gap-1", related_claim_ids=("cl-1",))
    oq = make_open_question(related_gap_ids=("gap-1",), related_claim_ids=("cl-1",))
    defaults: dict[str, Any] = {
        "request": make_research_request(),
        "status": ResearchStatus.COMPLETE,
        "sources": (source,),
        "evidence": (ev,),
        "claims": (cl,),
        "contradictions": (),
        "gaps": (gap,),
        "open_questions": (oq,),
        "completed_at": FIXED_TS,
    }
    defaults.update(kwargs)
    return ResearchResult(**defaults)


@pytest.fixture
def sample_source() -> Source:
    return make_source()


@pytest.fixture
def sample_provenance() -> Provenance:
    return make_provenance()


@pytest.fixture
def sample_evidence() -> EvidenceItem:
    return make_evidence_item()


@pytest.fixture
def sample_claim() -> Claim:
    return make_claim()


@pytest.fixture
def sample_request() -> ResearchRequest:
    return make_research_request()


@pytest.fixture
def sample_result() -> ResearchResult:
    return make_full_result()
