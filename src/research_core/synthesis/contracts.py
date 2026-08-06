"""
RC7 synthesis contracts.

These types represent the structured output of the synthesis stage.
SynthesisSection, SynthesisCitation, and SynthesisDiagnostics carry the
full structured synthesis. SynthesisConfig controls what sections are
emitted and how they are labelled.

None of these types import from contracts.result or analysis.contracts;
that keeps the import graph acyclic when contracts.result imports them.
"""

from __future__ import annotations

import hashlib
import json
import types
from dataclasses import dataclass, field
from enum import StrEnum

from research_core.contracts.common import EMPTY_METADATA, Metadata, _to_proxy
from research_core.exceptions import ContractValidationError


class SynthesisStatus(StrEnum):
    """Outcome of a synthesis run.

    COMPLETE — all configured sections were emitted without errors.
    PARTIAL  — some sections could not be emitted; result may be incomplete.
    FAILED   — synthesis raised and was caught; no sections were emitted.
    SKIPPED  — no synthesizer was configured.
    """

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class SynthesisSection:
    """One titled section of a structured synthesis.

    section_id: deterministic SHA256-based ID.
    claim_ids: IDs of ExtractedClaims whose text appears in body.
    evidence_ids: IDs of ranked evidence items referenced in body.
    source_ids: IDs of sources referenced in body.
    order: zero-based position in the synthesis output.
    """

    section_id: str
    title: str
    body: str = ""
    claim_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = field(default_factory=tuple)
    source_ids: tuple[str, ...] = field(default_factory=tuple)
    order: int = 0
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.section_id.strip():
            raise ContractValidationError("SynthesisSection.section_id must not be empty")
        if not self.title.strip():
            raise ContractValidationError("SynthesisSection.title must not be empty")
        if self.order < 0:
            raise ContractValidationError(
                f"SynthesisSection.order must be >= 0, got {self.order}"
            )
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class SynthesisCitation:
    """A traceable link from a synthesis section to a claim and its evidence.

    citation_id: deterministic SHA256-based ID per the RC7 citation formula.
    label: short human-readable label (e.g. "[1]" or "cit-abc123").
    """

    citation_id: str
    claim_id: str
    evidence_id: str
    source_id: str
    section_id: str
    label: str = ""
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not self.citation_id.strip():
            raise ContractValidationError("SynthesisCitation.citation_id must not be empty")
        if not self.claim_id.strip():
            raise ContractValidationError("SynthesisCitation.claim_id must not be empty")
        if not self.evidence_id.strip():
            raise ContractValidationError("SynthesisCitation.evidence_id must not be empty")
        if not self.source_id.strip():
            raise ContractValidationError("SynthesisCitation.source_id must not be empty")
        if not self.section_id.strip():
            raise ContractValidationError("SynthesisCitation.section_id must not be empty")
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))


@dataclass(frozen=True)
class SynthesisDiagnostics:
    """Execution diagnostics for a synthesis run.

    Counts describe the input and what was used vs. unused.
    configuration_fingerprint: SHA256 of the SynthesisConfig.
    """

    input_source_count: int
    input_evidence_count: int
    input_claim_count: int
    input_gap_count: int
    claims_used: int
    claims_unused: int
    evidence_used: int
    evidence_unused: int
    sections_emitted: int
    citations_emitted: int
    configuration_fingerprint: str
    synthesizer: str
    synthesizer_version: str

    def __post_init__(self) -> None:
        for name, val in (
            ("input_source_count", self.input_source_count),
            ("input_evidence_count", self.input_evidence_count),
            ("input_claim_count", self.input_claim_count),
            ("input_gap_count", self.input_gap_count),
            ("claims_used", self.claims_used),
            ("claims_unused", self.claims_unused),
            ("evidence_used", self.evidence_used),
            ("evidence_unused", self.evidence_unused),
            ("sections_emitted", self.sections_emitted),
            ("citations_emitted", self.citations_emitted),
        ):
            if val < 0:
                raise ContractValidationError(
                    f"SynthesisDiagnostics.{name} must be >= 0, got {val}"
                )


@dataclass(frozen=True)
class SynthesisConfig:
    """Controls which sections DeterministicSynthesizer emits.

    fingerprint: SHA256 over all config fields — used for citation/section IDs
    so they are stable across process restarts with the same config.
    """

    include_summary: bool = True
    include_claims_section: bool = True
    include_quality_section: bool = True
    include_gaps_section: bool = True
    include_limitations_section: bool = True
    maximum_claims_per_section: int = 100
    maximum_sections: int = 20
    synthesizer_version: str = "1"

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(
            {
                "include_summary": self.include_summary,
                "include_claims_section": self.include_claims_section,
                "include_quality_section": self.include_quality_section,
                "include_gaps_section": self.include_gaps_section,
                "include_limitations_section": self.include_limitations_section,
                "maximum_claims_per_section": self.maximum_claims_per_section,
                "maximum_sections": self.maximum_sections,
                "synthesizer_version": self.synthesizer_version,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


_DEFAULT_CONFIG = SynthesisConfig()

__all__ = [
    "SynthesisStatus",
    "SynthesisSection",
    "SynthesisCitation",
    "SynthesisDiagnostics",
    "SynthesisConfig",
    "_DEFAULT_CONFIG",
]
