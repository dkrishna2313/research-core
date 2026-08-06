"""
Tests for request validation and profile resolution.
"""

from __future__ import annotations

import pytest

from research_core.contracts.request import ResearchRequest
from research_core.engine import ResearchEngine
from research_core.exceptions import ProviderExecutionError, UnknownProfileError
from tests.engine.conftest import (
    FixedKnowledgeProvider,
    FixedProfileProvider,
    fixed_clock,
    make_evidence,
    make_source,
)


@pytest.mark.engine
class TestRequestValidation:
    def test_empty_question_raises(self) -> None:
        from research_core.exceptions import InvalidResearchRequestError

        with pytest.raises(InvalidResearchRequestError):
            ResearchRequest(question="")

    def test_whitespace_only_question_raises(self) -> None:
        from research_core.exceptions import InvalidResearchRequestError

        with pytest.raises(InvalidResearchRequestError):
            ResearchRequest(question="   ")


@pytest.mark.engine
class TestProfileResolution:
    def test_unknown_profile_raises(self) -> None:
        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            profile_provider=FixedProfileProvider({"known": "Known profile"}),
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            clock=fixed_clock,
        )
        with pytest.raises(UnknownProfileError):
            engine.run(ResearchRequest(question="test", profiles=("unknown-profile",)))

    def test_known_profile_resolves_successfully(self) -> None:
        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            profile_provider=FixedProfileProvider({"my-profile": "My Profile"}),
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            clock=fixed_clock,
        )
        result = engine.run(
            ResearchRequest(question="test", profiles=("my-profile",))
        )
        assert result is not None

    def test_profiles_requested_but_no_provider_raises(self) -> None:
        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            profile_provider=None,
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            clock=fixed_clock,
        )
        with pytest.raises(ProviderExecutionError):
            engine.run(ResearchRequest(question="test", profiles=("some-profile",)))

    def test_no_profiles_skips_resolution(self) -> None:
        from research_core.contracts.trace import TraceEventStatus, TraceStage

        src = make_source()
        ev = make_evidence()
        engine = ResearchEngine(
            knowledge_provider=FixedKnowledgeProvider((src,), (ev,)),
            clock=fixed_clock,
        )
        result = engine.run(ResearchRequest(question="test"))
        assert result.trace is not None
        profile_events = [
            e for e in result.trace.events
            if e.stage == TraceStage.PROFILE_RESOLUTION
        ]
        # Should be skipped
        assert all(e.status == TraceEventStatus.SKIPPED for e in profile_events)
