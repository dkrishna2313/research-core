"""
research_core.normalization — evidence normalization and ranking layer.

Public API:

Contracts:
  CapabilityStatus, AdapterCapability, CapabilityReport
  ComponentStatus, RankingComponent
  NormalizedEvidence, RankedEvidence
  DuplicateEvidence, ExcludedEvidence
  RankingDiagnostics, EvidenceRankingResult

Config:
  SegmentationConfig, RankingWeights, RankingConfig, NormalizationConfig

Convenience classes:
  EvidenceNormalizer, EvidenceRanker

Functions:
  normalize_evidence, segment_evidence, detect_duplicates, rank_evidence
  capability_report_for_knowledge, capability_report_for_web
"""

from __future__ import annotations

from research_core.normalization.capabilities import (
    capability_report_for_knowledge,
    capability_report_for_web,
)
from research_core.normalization.config import (
    NormalizationConfig,
    RankingConfig,
    RankingWeights,
    SegmentationConfig,
)
from research_core.normalization.contracts import (
    AdapterCapability,
    CapabilityReport,
    CapabilityStatus,
    ComponentStatus,
    DuplicateEvidence,
    EvidenceRankingResult,
    ExcludedEvidence,
    NormalizedEvidence,
    RankedEvidence,
    RankingComponent,
    RankingDiagnostics,
)
from research_core.normalization.deduplicate import detect_duplicates
from research_core.normalization.normalize import normalize_evidence
from research_core.normalization.normalizer import EvidenceNormalizer
from research_core.normalization.ranker import EvidenceRanker
from research_core.normalization.ranking import rank_evidence
from research_core.normalization.segmenter import segment_evidence

__all__ = [
    # contracts
    "CapabilityStatus",
    "AdapterCapability",
    "CapabilityReport",
    "ComponentStatus",
    "RankingComponent",
    "NormalizedEvidence",
    "RankedEvidence",
    "DuplicateEvidence",
    "ExcludedEvidence",
    "RankingDiagnostics",
    "EvidenceRankingResult",
    # config
    "SegmentationConfig",
    "RankingWeights",
    "RankingConfig",
    "NormalizationConfig",
    # convenience classes
    "EvidenceNormalizer",
    "EvidenceRanker",
    # functions
    "normalize_evidence",
    "segment_evidence",
    "detect_duplicates",
    "rank_evidence",
    "capability_report_for_knowledge",
    "capability_report_for_web",
]
