"""
Configuration contracts for RC5 claim extraction.

All configuration objects are immutable. The configuration fingerprint is a
deterministic SHA256-based digest that changes when any semantic field changes
and is stable across processes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from research_core.exceptions import ContractValidationError


@dataclass(frozen=True)
class ClaimExtractionConfig:
    """Configuration for a claim extraction run.

    All fields are immutable. The fingerprint property is a stable,
    cross-process deterministic digest of the semantic configuration.

    minimum_claim_characters: reject candidates shorter than this.
    maximum_claim_characters: reject candidates longer than this.
    split_clauses: if True, attempt clause-level splitting within sentences.
    preserve_questions: if True, keep question sentences as claims.
    preserve_commands: if True, keep imperative sentences as claims.
    include_rejections: if True, populate ClaimExtractionResult.rejections.
    deduplicate_exact: if True, collapse exact duplicates.
    normalize_whitespace: if True, collapse repeated whitespace in normalized_text.
    normalization_version: version tag for the normalization algorithm.
    extractor_version: version tag for the extractor algorithm.
    """

    minimum_claim_characters: int = 10
    maximum_claim_characters: int = 2000
    split_clauses: bool = True
    preserve_questions: bool = False
    preserve_commands: bool = False
    include_rejections: bool = True
    deduplicate_exact: bool = True
    normalize_whitespace: bool = True
    normalization_version: str = "1"
    extractor_version: str = "1"

    def __post_init__(self) -> None:
        if self.minimum_claim_characters <= 0:
            raise ContractValidationError(
                f"minimum_claim_characters must be > 0, got {self.minimum_claim_characters}"
            )
        if self.maximum_claim_characters <= 0:
            raise ContractValidationError(
                f"maximum_claim_characters must be > 0, got {self.maximum_claim_characters}"
            )
        if self.minimum_claim_characters > self.maximum_claim_characters:
            raise ContractValidationError(
                f"minimum_claim_characters ({self.minimum_claim_characters}) must be "
                f"<= maximum_claim_characters ({self.maximum_claim_characters})"
            )
        if not self.normalization_version.strip():
            raise ContractValidationError("normalization_version must not be empty")
        if not self.extractor_version.strip():
            raise ContractValidationError("extractor_version must not be empty")

    @property
    def fingerprint(self) -> str:
        """Deterministic SHA256-based digest of all semantic configuration fields.

        Stable across processes. Changes whenever any field value changes.
        Dictionary key ordering does not affect the result (sort_keys=True).
        """
        cfg_dict = {
            "minimum_claim_characters": self.minimum_claim_characters,
            "maximum_claim_characters": self.maximum_claim_characters,
            "split_clauses": self.split_clauses,
            "preserve_questions": self.preserve_questions,
            "preserve_commands": self.preserve_commands,
            "deduplicate_exact": self.deduplicate_exact,
            "normalize_whitespace": self.normalize_whitespace,
            "normalization_version": self.normalization_version,
            "extractor_version": self.extractor_version,
        }
        serialized = json.dumps(cfg_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
