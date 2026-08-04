"""
Rendering protocol.

Renderer[OutputT] is a generic protocol for converting a ResearchResult
into a caller-specified output format. The framework does not prescribe
what a rendered output looks like — implementations decide.

The generic parameter OutputT allows type-safe rendering to Markdown strings,
HTML, PDF bytes, dataframes, or any other format without coupling the
framework to a specific output type.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from research_core.contracts.result import ResearchResult

OutputT_co = TypeVar("OutputT_co", covariant=True)


@runtime_checkable
class Renderer(Protocol[OutputT_co]):
    """Structural generic protocol for result rendering.

    render() converts a ResearchResult to the implementation-defined
    output type.  Implementations are responsible for any format-specific
    serialization, encoding, or layout decisions.

    Example concrete types:
        Renderer[str]        — Markdown or plain text output
        Renderer[bytes]      — PDF or binary format output
        Renderer[dict]       — JSON-serializable dict output
    """

    def render(self, result: ResearchResult) -> OutputT_co:
        """Convert a research result to the target output format."""
        ...
