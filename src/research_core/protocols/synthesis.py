"""
Synthesis protocol.

Synthesizer converts a structured evidence set into a narrative answer.
The protocol is provider-based: no LLM SDK is coupled to the framework.
Deterministic synthesis (e.g. template-based) must remain possible.

Returns SynthesisResult directly — not ResearchResult. The engine
assembles the final ResearchResult.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from research_core.contracts.claims import Claim
from research_core.contracts.contradictions import Contradiction
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.gaps import OpenQuestion, ResearchGap
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import SynthesisResult


@runtime_checkable
class Synthesizer(Protocol):
    """Structural protocol for research synthesis.

    synthesize() receives the full structured output from the analysis
    stage and returns a SynthesisResult.

    Implementations may call an LLM, apply template rules, or produce
    deterministic output. The engine does not assume any particular
    synthesis strategy.

    Raises:
        ProviderUnavailableError: if the synthesis backend is not reachable.
        ProviderExecutionError: if synthesis fails after the backend is reached.
    """

    def synthesize(
        self,
        request: ResearchRequest,
        evidence: tuple[EvidenceItem, ...],
        claims: tuple[Claim, ...],
        contradictions: tuple[Contradiction, ...],
        gaps: tuple[ResearchGap, ...],
        open_questions: tuple[OpenQuestion, ...],
    ) -> SynthesisResult:
        """Synthesize evidence and claims into a structured narrative."""
        ...
