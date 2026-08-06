"""
Tests for empty-evidence behavior.

Empty evidence is never a successful complete result.
The engine raises when no evidence is retrieved from any provider.
"""

from __future__ import annotations

import pytest

from research_core.engine import ResearchEngine
from research_core.exceptions import ProviderExecutionError
from tests.engine.conftest import (
    EmptyKnowledgeProvider,
    FailingKnowledgeProvider,
    fixed_clock,
)


@pytest.mark.engine
class TestEmptyEvidence:
    def test_empty_knowledge_raises_provider_error(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = ResearchEngine(
            knowledge_provider=EmptyKnowledgeProvider(),
            clock=fixed_clock,
        )
        with pytest.raises(ProviderExecutionError):
            engine.run(ResearchRequest(question="test empty"))

    def test_failing_knowledge_no_web_raises(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = ResearchEngine(
            knowledge_provider=FailingKnowledgeProvider(),
            clock=fixed_clock,
        )
        with pytest.raises(ProviderExecutionError):
            engine.run(ResearchRequest(question="test no evidence"))

    def test_no_providers_raises(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = ResearchEngine(clock=fixed_clock)
        with pytest.raises(ProviderExecutionError):
            engine.run(ResearchRequest(question="test no providers"))

    def test_empty_knowledge_no_web_configured_raises(self) -> None:
        from research_core.contracts.request import ResearchRequest

        engine = ResearchEngine(
            knowledge_provider=EmptyKnowledgeProvider(),
            web_search_provider=None,
            clock=fixed_clock,
        )
        with pytest.raises(ProviderExecutionError):
            engine.run(ResearchRequest(question="test", use_web=False))
