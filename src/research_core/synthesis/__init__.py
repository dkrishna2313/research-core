"""
research_core.synthesis — deterministic synthesis implementation.

The Synthesizer protocol is defined in research_core.protocols.synthesis.
This package provides the DeterministicSynthesizer implementation.

Synthesis is evidence-grounded. Every synthesized statement is traceable
to extracted claims and supporting evidence. Synthesis does not imply
verification, truth, consensus, or corroboration.
"""

from __future__ import annotations

from research_core.synthesis.deterministic import DeterministicSynthesizer

__all__ = ["DeterministicSynthesizer"]
