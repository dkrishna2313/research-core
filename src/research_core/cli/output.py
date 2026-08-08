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


def render_result(
    result: ResearchResult,
    fmt: OutputFormat,
    *,
    answer_only: bool = False,
    answer_plus: bool = False,
) -> str:
    """Render *result* according to *fmt*.

    answer_only: synthesized answer sections only (no diagnostics, no citations).
    answer_plus: answer with brief diagnostic context and source-titled citations.
    Both are incompatible with JSON — the caller must reject those combos.

    Returns a string ending with exactly one newline.
    Raises RuntimeError if rendering fails (caller maps to OUTPUT_FAILURE).
    """
    if fmt == OutputFormat.JSON:
        return _render_json(result)
    if answer_only:
        return _render_markdown_answer_only(result)
    if answer_plus:
        return _render_markdown_answer_plus(result)
    return _render_markdown(result)


def _render_markdown(result: ResearchResult) -> str:
    from research_core.renderers import MarkdownRenderer

    return MarkdownRenderer().render(result)


def _render_markdown_answer_only(result: ResearchResult) -> str:
    from research_core.renderers import MarkdownRenderer

    return MarkdownRenderer().render_answer_only(result)


def _render_markdown_answer_plus(result: ResearchResult) -> str:
    from research_core.renderers import MarkdownRenderer

    return MarkdownRenderer().render_answer_plus(result)


def _render_json(result: ResearchResult) -> str:
    serialized = serialize(result)
    return json.dumps(serialized, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
