"""Tests for ResearchRequest contract."""

from __future__ import annotations

import types

import pytest

from research_core.contracts.request import ResearchRequest
from research_core.exceptions import InvalidResearchRequestError


class TestResearchRequestConstruction:
    def test_minimal_construction(self) -> None:
        req = ResearchRequest(question="What is the carbon cycle?")
        assert req.question == "What is the carbon cycle?"

    def test_question_is_stripped(self) -> None:
        req = ResearchRequest(question="  What is the carbon cycle?  ")
        assert req.question == "What is the carbon cycle?"

    def test_empty_question_rejected(self) -> None:
        with pytest.raises(InvalidResearchRequestError, match="question"):
            ResearchRequest(question="")

    def test_whitespace_only_question_rejected(self) -> None:
        with pytest.raises(InvalidResearchRequestError, match="question"):
            ResearchRequest(question="   ")

    def test_defaults(self) -> None:
        req = ResearchRequest(question="Q?")
        assert req.use_knowledge is True
        assert req.use_web is False
        assert req.max_knowledge_results == 10
        assert req.max_web_results == 5
        assert req.max_web_pages == 5
        assert req.language == "en"
        assert req.strict is False
        assert req.profiles == ()
        assert req.as_of_date is None

    def test_metadata_wrapped_in_proxy(self) -> None:
        req = ResearchRequest(question="Q?", metadata={"k": "v"})
        assert isinstance(req.metadata, types.MappingProxyType)
        assert req.metadata["k"] == "v"

    def test_metadata_proxy_passthrough(self) -> None:
        proxy = types.MappingProxyType({"k": "v"})
        req = ResearchRequest(question="Q?", metadata=proxy)
        assert req.metadata is proxy


class TestResearchRequestProfiles:
    def test_profiles_tuple_stored(self) -> None:
        req = ResearchRequest(question="Q?", profiles=("climate", "energy"))
        assert req.profiles == ("climate", "energy")

    def test_blank_profile_rejected(self) -> None:
        with pytest.raises(InvalidResearchRequestError, match="profile"):
            ResearchRequest(question="Q?", profiles=("climate", "  "))

    def test_duplicate_profiles_deduplicated(self) -> None:
        req = ResearchRequest(question="Q?", profiles=("a", "b", "a"))
        assert req.profiles == ("a", "b")

    def test_has_profiles_false_when_empty(self) -> None:
        req = ResearchRequest(question="Q?")
        assert req.has_profiles is False

    def test_has_profiles_true_when_set(self) -> None:
        req = ResearchRequest(question="Q?", profiles=("climate",))
        assert req.has_profiles is True


class TestResearchRequestLimits:
    def test_zero_max_knowledge_results_rejected(self) -> None:
        with pytest.raises(InvalidResearchRequestError):
            ResearchRequest(question="Q?", max_knowledge_results=0)

    def test_negative_max_web_results_rejected(self) -> None:
        with pytest.raises(InvalidResearchRequestError):
            ResearchRequest(question="Q?", max_web_results=-1)

    def test_zero_max_web_pages_rejected(self) -> None:
        with pytest.raises(InvalidResearchRequestError):
            ResearchRequest(question="Q?", max_web_pages=0)


class TestResearchRequestImmutability:
    def test_is_frozen(self) -> None:
        req = ResearchRequest(question="Q?")
        with pytest.raises((AttributeError, TypeError)):
            req.question = "other"  # type: ignore[misc]
