"""
research_core.contracts — typed domain contracts.

All public types in the contract layer are re-exported here. Callers that
only interact with results should import from this package directly rather
than from individual sub-modules.

Internal helpers (e.g. _to_proxy) are intentionally excluded from __all__.
"""

from __future__ import annotations

from research_core.contracts.claims import Claim, ClaimStatus, ClaimType
from research_core.contracts.common import (
    EMPTY_METADATA,
    ClaimId,
    ContradictionId,
    DocumentId,
    EvidenceId,
    Metadata,
    ProfileId,
    ResearchGapId,
    SourceId,
    SourceType,
    TraceEventId,
)
from research_core.contracts.contradictions import (
    Contradiction,
    ContradictionResolutionStatus,
    ContradictionSeverity,
    ContradictionType,
)
from research_core.contracts.evidence import (
    EvidenceClaimLink,
    EvidenceItem,
    EvidenceRelationship,
)
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
from research_core.contracts.serialization import serialize
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.contracts.trace import ResearchTrace, TraceEvent, TraceEventStatus, TraceStage

__all__ = [
    # identifiers
    "ClaimId",
    "ContradictionId",
    "DocumentId",
    "EvidenceId",
    "Metadata",
    "ProfileId",
    "ResearchGapId",
    "SourceId",
    "TraceEventId",
    # metadata sentinel
    "EMPTY_METADATA",
    # enums
    "ClaimStatus",
    "ClaimType",
    "ContradictionResolutionStatus",
    "ContradictionSeverity",
    "ContradictionType",
    "EvidenceRelationship",
    "GapSeverity",
    "GapStatus",
    "GapType",
    "QuestionPriority",
    "ResearchStatus",
    "SourceType",
    "TraceEventStatus",
    "TraceStage",
    # dataclasses
    "Claim",
    "Contradiction",
    "EvidenceClaimLink",
    "EvidenceItem",
    "EvidenceQuality",
    "OpenQuestion",
    "Provenance",
    "QualityDiagnostics",
    "QualityDimension",
    "ResearchGap",
    "ResearchRequest",
    "ResearchResult",
    "ResearchTrace",
    "Source",
    "SynthesisResult",
    "TraceEvent",
    # utilities
    "serialize",
]
