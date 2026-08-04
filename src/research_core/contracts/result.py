"""
Research result contracts.

ResearchResult is the top-level output object. It exists only when the
pipeline produced useful output. Failures before useful output is available
raise typed exceptions; they do not produce a ResearchResult with a failed
status. Therefore ResearchStatus has only COMPLETE and PARTIAL — no FAILED.

ResearchResult validates full graph consistency on construction:
- all IDs within each collection are unique
- all cross-collection references resolve
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from research_core.contracts.claims import Claim
from research_core.contracts.common import (
    EMPTY_METADATA,
    ClaimId,
    EvidenceId,
    Metadata,
    SourceId,
    _to_proxy,
)
from research_core.contracts.contradictions import Contradiction
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import OpenQuestion, ResearchGap
from research_core.contracts.quality import QualityDiagnostics
from research_core.contracts.request import ResearchRequest
from research_core.contracts.sources import Source
from research_core.contracts.trace import ResearchTrace
from research_core.exceptions import ContractValidationError


class ResearchStatus(StrEnum):
    """Outcome of a research pipeline run.

    COMPLETE — all configured retrieval and analysis steps succeeded;
               the result reflects the full configured scope.
    PARTIAL  — the pipeline produced useful output but some steps did not
               complete (e.g. one provider failed, web retrieval timed out).
               The caller receives the partial result instead of an exception;
               gaps and quality diagnostics describe what is missing.

    There is no FAILED status. A result object only exists when there is
    meaningful evidence to report. Failures before any useful output raise
    typed exceptions (ProviderUnavailableError, ProviderExecutionError, etc.).
    """

    COMPLETE = "complete"
    PARTIAL = "partial"


@dataclass(frozen=True)
class SynthesisResult:
    """Output from a Synthesizer provider.

    narrative: the synthesized prose answer to the research question.
    key_findings: ordered list of discrete findings surfaced by synthesis.
    synthesis_model: optional identifier for the model or method used.
    synthesized_at: when synthesis completed; must be timezone-aware.
    confidence: overall synthesis confidence in [0.0, 1.0]; None = not assessed.
    metadata: caller-supplied passthrough; not interpreted by the framework.
    """

    narrative: str
    key_findings: tuple[str, ...] = field(default_factory=tuple)
    synthesis_model: str | None = None
    synthesized_at: datetime | None = None
    confidence: float | None = None
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.narrative.strip():
            raise ContractValidationError("SynthesisResult.narrative must not be empty")
        if self.synthesized_at is not None and self.synthesized_at.tzinfo is None:
            raise ContractValidationError(
                "SynthesisResult.synthesized_at must be timezone-aware if provided"
            )
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ContractValidationError(
                f"SynthesisResult.confidence must be in [0.0, 1.0], got {self.confidence}"
            )
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class ResearchResult:
    """Top-level output of a research pipeline run.

    All collection IDs must be unique within their type. All cross-collection
    references must resolve to existing items. These invariants are verified
    on construction; ContractValidationError is raised on violation.

    synthesis: present when a Synthesizer was configured and succeeded.
               If the synthesizer failed after evidence retrieval, the result
               is returned with status=PARTIAL and no synthesis.
    quality: present when quality analysis ran; dimensions are independently
             accessible.
    trace: present when tracing is enabled; may be empty (no events).
    """

    request: ResearchRequest
    status: ResearchStatus
    sources: tuple[Source, ...]
    evidence: tuple[EvidenceItem, ...]
    claims: tuple[Claim, ...]
    contradictions: tuple[Contradiction, ...]
    gaps: tuple[ResearchGap, ...]
    open_questions: tuple[OpenQuestion, ...]
    synthesis: SynthesisResult | None = None
    quality: QualityDiagnostics | None = None
    trace: ResearchTrace | None = None
    completed_at: datetime | None = None
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:  # noqa: C901
        if self.completed_at is not None and self.completed_at.tzinfo is None:
            raise ContractValidationError(
                "ResearchResult.completed_at must be timezone-aware if provided"
            )
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))

        # A COMPLETE result with no sources at all contains no meaningful output.
        # Callers that have useful partial content should use status=PARTIAL.
        if self.status == ResearchStatus.COMPLETE and not self.sources:
            raise ContractValidationError(
                "a COMPLETE ResearchResult must contain at least one Source; "
                "use status=PARTIAL when the result is incomplete"
            )

        # --- unique-ID checks ---
        self._check_unique_ids(
            [s.source_id for s in self.sources], "source_id", "sources"
        )
        self._check_unique_ids(
            [e.evidence_id for e in self.evidence], "evidence_id", "evidence"
        )
        self._check_unique_ids(
            [c.claim_id for c in self.claims], "claim_id", "claims"
        )
        self._check_unique_ids(
            [c.contradiction_id for c in self.contradictions],
            "contradiction_id",
            "contradictions",
        )
        self._check_unique_ids(
            [g.gap_id for g in self.gaps], "gap_id", "gaps"
        )

        # --- build index sets for reference checks ---
        source_ids: set[SourceId] = {s.source_id for s in self.sources}
        evidence_ids: set[EvidenceId] = {e.evidence_id for e in self.evidence}
        claim_ids: set[ClaimId] = {c.claim_id for c in self.claims}
        gap_ids = {g.gap_id for g in self.gaps}

        # --- evidence → source ---
        for ev in self.evidence:
            if ev.source_id not in source_ids:
                raise ContractValidationError(
                    f"EvidenceItem {ev.evidence_id!r} references unknown source_id "
                    f"{ev.source_id!r}"
                )
            for link in ev.claim_links:
                if link.claim_id not in claim_ids:
                    raise ContractValidationError(
                        f"EvidenceClaimLink on evidence {ev.evidence_id!r} references "
                        f"unknown claim_id {link.claim_id!r}"
                    )

        # --- claim → evidence ---
        for cl in self.claims:
            for eid in cl.supporting_evidence_ids:
                if eid not in evidence_ids:
                    raise ContractValidationError(
                        f"Claim {cl.claim_id!r} supporting_evidence_ids references "
                        f"unknown evidence_id {eid!r}"
                    )
            for eid in cl.conflicting_evidence_ids:
                if eid not in evidence_ids:
                    raise ContractValidationError(
                        f"Claim {cl.claim_id!r} conflicting_evidence_ids references "
                        f"unknown evidence_id {eid!r}"
                    )

        # --- contradiction → claims/evidence ---
        for con in self.contradictions:
            for cid in con.claim_ids:
                if cid not in claim_ids:
                    raise ContractValidationError(
                        f"Contradiction {con.contradiction_id!r} references unknown "
                        f"claim_id {cid!r}"
                    )
            for eid in con.evidence_ids:
                if eid not in evidence_ids:
                    raise ContractValidationError(
                        f"Contradiction {con.contradiction_id!r} references unknown "
                        f"evidence_id {eid!r}"
                    )

        # --- gap → claims/evidence ---
        for gap in self.gaps:
            for cid in gap.related_claim_ids:
                if cid not in claim_ids:
                    raise ContractValidationError(
                        f"ResearchGap {gap.gap_id!r} references unknown claim_id "
                        f"{cid!r}"
                    )
            for eid in gap.related_evidence_ids:
                if eid not in evidence_ids:
                    raise ContractValidationError(
                        f"ResearchGap {gap.gap_id!r} references unknown evidence_id "
                        f"{eid!r}"
                    )

        # --- open question → claims/gaps ---
        for oq in self.open_questions:
            for cid in oq.related_claim_ids:
                if cid not in claim_ids:
                    raise ContractValidationError(
                        f"OpenQuestion {oq.question[:40]!r} references unknown "
                        f"claim_id {cid!r}"
                    )
            for gid in oq.related_gap_ids:
                if gid not in gap_ids:
                    raise ContractValidationError(
                        f"OpenQuestion {oq.question[:40]!r} references unknown "
                        f"gap_id {gid!r}"
                    )

    @staticmethod
    def _check_unique_ids(ids: list[Any], field_name: str, collection: str) -> None:
        seen: set[Any] = set()
        for id_val in ids:
            if id_val in seen:
                raise ContractValidationError(
                    f"duplicate {field_name} {id_val!r} in {collection}"
                )
            seen.add(id_val)

    @property
    def is_complete(self) -> bool:
        return self.status == ResearchStatus.COMPLETE

    @property
    def is_partial(self) -> bool:
        return self.status == ResearchStatus.PARTIAL
