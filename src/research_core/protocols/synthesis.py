"""
Synthesis protocol (RC7 aligned).

Synthesizer converts structured evidence into a narrative answer.
The protocol is provider-based: no LLM SDK is coupled to the framework.
Deterministic synthesis (e.g. template-based) must remain possible.

SynthesisInput carries all pipeline artifacts the synthesizer needs;
the engine assembles it before calling the synthesizer. This keeps the
synthesizer interface stable regardless of which pipeline components ran.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from research_core.analysis.contracts import GapAnalysisResult
from research_core.claims.contracts import ExtractedClaim
from research_core.contracts.result import SynthesisResult
from research_core.contracts.sources import Source
from research_core.normalization.contracts import RankedEvidence
from research_core.synthesis.contracts import SynthesisConfig


@dataclass(frozen=True)
class SynthesisInput:
    """All pipeline artifacts passed to a Synthesizer.

    sources: deduplicated sources retrieved during this run.
    evidence: ranked evidence from the RC4 normalizer/ranker (empty when
              the RC4 pipeline was not used).
    claims: extracted claims from the RC5 extractor (empty when RC5 was not used).
    gap_analysis: full RC6 gap analysis result (None when RC6 was not used).
    request_text: the original research question verbatim.
    """

    request_text: str
    sources: tuple[Source, ...]
    evidence: tuple[RankedEvidence, ...] = field(default_factory=tuple)
    claims: tuple[ExtractedClaim, ...] = field(default_factory=tuple)
    gap_analysis: GapAnalysisResult | None = None


@runtime_checkable
class Synthesizer(Protocol):
    """Structural protocol for research synthesis (RC7 aligned).

    synthesize() receives a SynthesisInput containing all pipeline artifacts
    and returns a SynthesisResult with structured sections and citations.

    Implementations may call an LLM, apply template rules, or produce
    deterministic output. The engine does not assume any particular strategy.

    Raises:
        ProviderUnavailableError: if the synthesis backend is not reachable.
        ProviderExecutionError: if synthesis fails after the backend is reached.
    """

    def synthesize(
        self,
        inputs: SynthesisInput,
        *,
        config: SynthesisConfig | None = None,
    ) -> SynthesisResult:
        """Synthesize evidence and claims into a structured result."""
        ...
