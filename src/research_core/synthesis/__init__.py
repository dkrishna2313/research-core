"""
research_core.synthesis — structured synthesis implementation (RC7).

The Synthesizer protocol and SynthesisInput are in research_core.protocols.synthesis.
This package provides the DeterministicSynthesizer implementation and the
RC7 synthesis contracts (SynthesisSection, SynthesisCitation, etc.).

Synthesis is evidence-grounded. Every synthesized statement is traceable
to extracted claims and supporting evidence. Synthesis does not imply
verification, truth, consensus, or corroboration.

Exports are loaded lazily to avoid circular imports (contracts.result
imports synthesis.contracts; deterministic.py imports contracts.result).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from research_core.synthesis.contracts import (
        SynthesisCitation,
        SynthesisConfig,
        SynthesisDiagnostics,
        SynthesisSection,
        SynthesisStatus,
    )
    from research_core.synthesis.deterministic import DeterministicSynthesizer


def __getattr__(name: str) -> object:
    if name == "DeterministicSynthesizer":
        from research_core.synthesis.deterministic import (
            DeterministicSynthesizer as _DS,
        )
        return _DS
    if name == "SynthesisConfig":
        from research_core.synthesis.contracts import SynthesisConfig as _SC
        return _SC
    if name == "SynthesisCitation":
        from research_core.synthesis.contracts import SynthesisCitation as _SCit
        return _SCit
    if name == "SynthesisDiagnostics":
        from research_core.synthesis.contracts import SynthesisDiagnostics as _SDi
        return _SDi
    if name == "SynthesisSection":
        from research_core.synthesis.contracts import SynthesisSection as _SSec
        return _SSec
    if name == "SynthesisStatus":
        from research_core.synthesis.contracts import SynthesisStatus as _SSt
        return _SSt
    raise AttributeError(f"module 'research_core.synthesis' has no attribute {name!r}")


__all__ = [
    "DeterministicSynthesizer",
    "SynthesisConfig",
    "SynthesisCitation",
    "SynthesisDiagnostics",
    "SynthesisSection",
    "SynthesisStatus",
]
