"""
RC5 claim extraction — public API.

Exports all public contracts, enumerations, configuration, the
ClaimExtractor protocol, and the DeterministicClaimExtractor implementation.

Usage:
    from research_core.claims import (
        DeterministicClaimExtractor,
        ClaimExtractionConfig,
        ClaimType,
        ClaimModality,
        ClaimPolarity,
    )

    extractor = DeterministicClaimExtractor()
    result = extractor.extract(ranked_evidence_items)
    for claim in result.claims:
        print(claim.claim_id, claim.claim_type, claim.modality)

See docs/claims/CLAIM_EXTRACTION.md for full documentation.
"""

from __future__ import annotations

from research_core.claims.config import ClaimExtractionConfig
from research_core.claims.contracts import (
    ClaimAttribution,
    ClaimExtractionDiagnostics,
    ClaimExtractionResult,
    ClaimModality,
    ClaimPolarity,
    ClaimQualifier,
    ClaimQualifierKind,
    ClaimRejection,
    ClaimScope,
    ClaimType,
    DuplicateClaim,
    ExtractedClaim,
    QuantitativeExpression,
    RejectionReason,
    TemporalExpression,
    TemporalKind,
)
from research_core.claims.extractor import ClaimExtractor, DeterministicClaimExtractor

__all__ = [
    # Enumerations
    "ClaimType",
    "ClaimModality",
    "ClaimPolarity",
    "ClaimQualifierKind",
    "TemporalKind",
    "RejectionReason",
    # Qualifier and expression types
    "ClaimQualifier",
    "QuantitativeExpression",
    "TemporalExpression",
    "ClaimAttribution",
    "ClaimScope",
    # Core claim contract
    "ExtractedClaim",
    # Result types
    "DuplicateClaim",
    "ClaimRejection",
    "ClaimExtractionDiagnostics",
    "ClaimExtractionResult",
    # Configuration
    "ClaimExtractionConfig",
    # Extractor protocol and implementation
    "ClaimExtractor",
    "DeterministicClaimExtractor",
]
