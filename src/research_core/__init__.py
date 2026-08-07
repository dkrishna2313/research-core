"""
research-core — domain-neutral research library.

RC8.1: live Knowledge CLI execution via --knowledge-store.

Importing this package does not trigger filesystem access, network access,
environment-variable loading, provider initialization, or legacy imports.

Public surface:
- research_core.contracts  — typed domain contracts (data layer)
- research_core.protocols  — provider protocol boundaries (interface layer)
- research_core.exceptions — typed exception hierarchy
- research_core.engine     — ResearchEngine orchestration
- research_core.synthesis  — DeterministicSynthesizer
- research_core.renderers  — MarkdownRenderer
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
from research_core.engine import ResearchEngine
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
from research_core.normalization import (
    AdapterCapability,
    CapabilityReport,
    CapabilityStatus,
    EvidenceNormalizer,
    EvidenceRanker,
    EvidenceRankingResult,
    NormalizationConfig,
    NormalizedEvidence,
    RankedEvidence,
    RankingConfig,
    SegmentationConfig,
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
from research_core.renderers import MarkdownRenderer
from research_core.synthesis import DeterministicSynthesizer

__version__ = "0.8.1"

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
    # engine / synthesis / renderers
    "ResearchEngine",
    "DeterministicSynthesizer",
    "MarkdownRenderer",
    # normalization
    "AdapterCapability",
    "CapabilityReport",
    "CapabilityStatus",
    "EvidenceNormalizer",
    "EvidenceRanker",
    "EvidenceRankingResult",
    "NormalizationConfig",
    "NormalizedEvidence",
    "RankedEvidence",
    "RankingConfig",
    "SegmentationConfig",
]
