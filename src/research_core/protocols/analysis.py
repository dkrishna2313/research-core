"""
Analysis layer protocols.

Three distinct analytical concerns are separated by protocol:

- ClaimExtractor     — derives structured Claims from raw evidence items
- ContradictionDetector — identifies Contradictions between claims/evidence
- GapAnalyzer        — identifies ResearchGaps and surfaces OpenQuestions

Each protocol is independently replaceable. The framework wires them together;
implementations do not know about each other.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from research_core.contracts.claims import Claim
from research_core.contracts.contradictions import Contradiction
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import OpenQuestion, ResearchGap
from research_core.contracts.request import ResearchRequest


@runtime_checkable
class ClaimExtractor(Protocol):
    """Structural protocol for extracting claims from evidence.

    extract() receives the full evidence pool for a research run and
    returns structured Claim objects. The implementation is responsible
    for assigning unique claim IDs.

    Returned claims may reference evidence IDs from the input items.
    The engine validates cross-references before constructing ResearchResult.
    """

    def extract(
        self,
        evidence: tuple[EvidenceItem, ...],
        request: ResearchRequest,
    ) -> tuple[Claim, ...]:
        """Extract structured claims from an evidence pool."""
        ...


@runtime_checkable
class ContradictionDetector(Protocol):
    """Structural protocol for detecting contradictions.

    detect() receives the full claim and evidence sets and returns
    structured Contradiction objects. The implementation is responsible
    for assigning unique contradiction IDs.

    Returned contradictions may reference claim IDs and evidence IDs
    from the input collections.
    """

    def detect(
        self,
        claims: tuple[Claim, ...],
        evidence: tuple[EvidenceItem, ...],
        request: ResearchRequest,
    ) -> tuple[Contradiction, ...]:
        """Detect contradictions across the claims and evidence pool."""
        ...


@runtime_checkable
class GapAnalyzer(Protocol):
    """Structural protocol for research gap analysis.

    analyze() receives claims, evidence, and contradictions and returns
    ResearchGap objects plus OpenQuestion objects that surface unresolved
    questions for the caller.

    The implementation is responsible for assigning unique gap IDs.
    """

    def analyze(
        self,
        claims: tuple[Claim, ...],
        evidence: tuple[EvidenceItem, ...],
        contradictions: tuple[Contradiction, ...],
        request: ResearchRequest,
    ) -> tuple[tuple[ResearchGap, ...], tuple[OpenQuestion, ...]]:
        """Identify research gaps and open questions."""
        ...
