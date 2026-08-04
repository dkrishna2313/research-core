"""
Configuration for evidence normalization, segmentation, and ranking.

All config objects are frozen dataclasses — create once, share freely.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from research_core.exceptions import ContractValidationError


@dataclass(frozen=True)
class SegmentationConfig:
    """Configuration for evidence segmentation.

    max_characters: hard upper bound per segment.
    target_characters: preferred segment length; segments aim for this size.
    overlap_characters: characters of overlap carried from end of previous segment.
    minimum_segment_characters: discard segments shorter than this (unless only one).
    preserve_paragraphs: prefer paragraph boundaries over mid-paragraph splits.
    version: incorporated into segment ID hashes; bump to invalidate cached IDs.
    """

    max_characters: int = 6000
    target_characters: int = 4500
    overlap_characters: int = 300
    minimum_segment_characters: int = 200
    preserve_paragraphs: bool = True
    version: str = "1"

    def __post_init__(self) -> None:
        if self.target_characters > self.max_characters:
            raise ContractValidationError(
                f"target_characters ({self.target_characters}) must not exceed "
                f"max_characters ({self.max_characters})"
            )
        if self.overlap_characters >= self.target_characters:
            raise ContractValidationError(
                f"overlap_characters ({self.overlap_characters}) must be less than "
                f"target_characters ({self.target_characters})"
            )


@dataclass(frozen=True)
class RankingWeights:
    """Weights for the six ranking dimensions.

    All weights must be in [0, 1] and their sum must be > 0.
    Default weights sum to exactly 1.0:
      retrieval=0.35 + relevance=0.25 + authority=0.15 +
      recency=0.10 + extraction_confidence=0.05 + provenance_completeness=0.10 = 1.0
    """

    retrieval: float = 0.35
    relevance: float = 0.25
    authority: float = 0.15
    recency: float = 0.10
    extraction_confidence: float = 0.05
    provenance_completeness: float = 0.10

    def __post_init__(self) -> None:
        for name, val in self._items():
            if not 0.0 <= val <= 1.0:
                raise ContractValidationError(
                    f"RankingWeights.{name} must be in [0, 1], got {val}"
                )
        if sum(v for _, v in self._items()) <= 0.0:
            raise ContractValidationError("RankingWeights must have at least one positive weight")

    def _items(self) -> list[tuple[str, float]]:
        return [
            ("retrieval", self.retrieval),
            ("relevance", self.relevance),
            ("authority", self.authority),
            ("recency", self.recency),
            ("extraction_confidence", self.extraction_confidence),
            ("provenance_completeness", self.provenance_completeness),
        ]


@dataclass(frozen=True)
class RankingConfig:
    """Configuration for evidence deduplication and ranking."""

    weights: RankingWeights = field(default_factory=RankingWeights)
    near_duplicate_threshold: float = 0.90
    missing_value_policy: str = "proportional"
    max_near_duplicate_comparisons: int = 1000

    def __post_init__(self) -> None:
        if not 0.0 < self.near_duplicate_threshold <= 1.0:
            raise ContractValidationError(
                f"near_duplicate_threshold must be in (0, 1], got {self.near_duplicate_threshold}"
            )
        if self.missing_value_policy != "proportional":
            raise ContractValidationError(
                f"unsupported missing_value_policy {self.missing_value_policy!r}; "
                f"only 'proportional' is supported"
            )

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            {
                "retrieval": self.weights.retrieval,
                "relevance": self.weights.relevance,
                "authority": self.weights.authority,
                "recency": self.weights.recency,
                "extraction_confidence": self.weights.extraction_confidence,
                "provenance_completeness": self.weights.provenance_completeness,
                "near_duplicate_threshold": self.near_duplicate_threshold,
                "missing_value_policy": self.missing_value_policy,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class NormalizationConfig:
    """Top-level configuration for the full normalization pipeline."""

    segmentation: SegmentationConfig = field(default_factory=SegmentationConfig)
    ranking: RankingConfig = field(default_factory=RankingConfig)
