"""
research-core — domain-neutral research library.

This package is currently in RC1 (Core Contracts and Package Boundary).
The research engine is not yet implemented.

Importing this package does not trigger filesystem access, network access,
environment-variable loading, provider initialization, or legacy imports.

Public surface:
- research_core.contracts  — typed domain contracts (data layer)
- research_core.protocols  — provider protocol boundaries (interface layer)
- research_core.exceptions — typed exception hierarchy
"""

from __future__ import annotations

from research_core.contracts import (
    EMPTY_METADATA,
    Claim,
    ClaimId,
    ClaimStatus,
    ClaimType,
    Contradiction,
    ContradictionId,
    ContradictionResolutionStatus,
    ContradictionSeverity,
    ContradictionType,
    DocumentId,
    EvidenceClaimLink,
    EvidenceId,
    EvidenceItem,
    EvidenceQuality,
    EvidenceRelationship,
    GapSeverity,
    GapStatus,
    GapType,
    Metadata,
    OpenQuestion,
    ProfileId,
    Provenance,
    QualityDiagnostics,
    QualityDimension,
    QuestionPriority,
    ResearchGap,
    ResearchGapId,
    ResearchRequest,
    ResearchResult,
    ResearchStatus,
    ResearchTrace,
    Source,
    SourceId,
    SourceType,
    SynthesisResult,
    TraceEvent,
    TraceEventId,
    TraceEventStatus,
    TraceStage,
    serialize,
)
from research_core.exceptions import (
    ContractValidationError,
    IncompleteResearchError,
    InvalidResearchRequestError,
    ProviderExecutionError,
    ProviderUnavailableError,
    ResearchCoreError,
    UnknownProfileError,
    UnsupportedConfigurationError,
)
from research_core.protocols import (
    ClaimExtractor,
    ContradictionDetector,
    GapAnalyzer,
    KnowledgeProvider,
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
    OutputT_co,
    ProfileProvider,
    Renderer,
    ResolvedProfile,
    Synthesizer,
    WebSearchProvider,
    WebSearchRequest,
    WebSearchResult,
)

__version__ = "0.3.0"

__all__ = [
    "__version__",
    # contracts — identifiers
    "ClaimId",
    "ContradictionId",
    "DocumentId",
    "EvidenceId",
    "Metadata",
    "ProfileId",
    "ResearchGapId",
    "SourceId",
    "TraceEventId",
    "EMPTY_METADATA",
    # contracts — enums
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
    # contracts — dataclasses
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
    # contracts — utilities
    "serialize",
    # exceptions
    "ContractValidationError",
    "IncompleteResearchError",
    "InvalidResearchRequestError",
    "ProviderExecutionError",
    "ProviderUnavailableError",
    "ResearchCoreError",
    "UnknownProfileError",
    "UnsupportedConfigurationError",
    # protocols
    "ClaimExtractor",
    "ContradictionDetector",
    "GapAnalyzer",
    "KnowledgeProvider",
    "KnowledgeRetrievalRequest",
    "KnowledgeRetrievalResult",
    "OutputT_co",
    "ProfileProvider",
    "Renderer",
    "ResolvedProfile",
    "Synthesizer",
    "WebSearchProvider",
    "WebSearchRequest",
    "WebSearchResult",
]
