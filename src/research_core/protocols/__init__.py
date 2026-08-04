"""
research_core.protocols — provider protocol boundaries.

All protocol types are re-exported here. Callers that implement providers
should import from this package directly.

The generic OutputT TypeVar is exported so callers can annotate their own
Renderer implementations without importing from the sub-module directly.
"""

from __future__ import annotations

from research_core.protocols.analysis import (
    ClaimExtractor,
    ContradictionDetector,
    GapAnalyzer,
)
from research_core.protocols.knowledge import (
    KnowledgeProvider,
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
)
from research_core.protocols.profiles import ProfileProvider, ResolvedProfile
from research_core.protocols.rendering import OutputT_co, Renderer
from research_core.protocols.synthesis import Synthesizer
from research_core.protocols.web import WebSearchProvider, WebSearchRequest

__all__ = [
    # knowledge
    "KnowledgeProvider",
    "KnowledgeRetrievalRequest",
    "KnowledgeRetrievalResult",
    # web
    "WebSearchProvider",
    "WebSearchRequest",
    # profiles
    "ProfileProvider",
    "ResolvedProfile",
    # analysis
    "ClaimExtractor",
    "ContradictionDetector",
    "GapAnalyzer",
    # synthesis
    "Synthesizer",
    # rendering
    "OutputT_co",
    "Renderer",
]
