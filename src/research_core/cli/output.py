"""
Output rendering for the research-core CLI.

render_result() converts a ResearchResult to a string in the requested format.
stdout: pure result text (Markdown or JSON) — no preamble, no status commentary.
"""

from __future__ import annotations

import json

from research_core.cli.config import OutputFormat
from research_core.contracts.result import ResearchResult
from research_core.contracts.serialization import serialize


def render_result(result: ResearchResult, fmt: OutputFormat) -> str:
    """Render *result* according to *fmt*.

    Returns a string ending with exactly one newline.
    Raises RuntimeError if rendering fails (caller maps to OUTPUT_FAILURE).
    """
    if fmt == OutputFormat.JSON:
        return _render_json(result)
    return _render_markdown(result)


def _render_markdown(result: ResearchResult) -> str:
    from research_core.renderers import MarkdownRenderer

    return MarkdownRenderer().render(result)


def _render_json(result: ResearchResult) -> str:
    serialized = serialize(result)
    return json.dumps(serialized, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
