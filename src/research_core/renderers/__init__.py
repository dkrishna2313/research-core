"""
research_core.renderers — result rendering implementations.

The Renderer protocol is defined in research_core.protocols.rendering.
This package provides the MarkdownRenderer implementation.

Rendering is pure presentation:
- accepts a ResearchResult
- returns formatted output
- does not mutate the result
- does not run providers
- does not synthesize new content
- does not change result status
"""

from __future__ import annotations

from research_core.renderers.markdown import MarkdownRenderer

__all__ = ["MarkdownRenderer"]
