"""Live integration tests for WebSearchAdapter.

These tests require network access and the ddgs, requests, and trafilatura packages.
They are gated behind the RUN_NETWORK_TESTS=1 environment variable.

Run with:
    RUN_NETWORK_TESTS=1 python3 -m pytest tests/adapters/web/test_integration.py -v
    RUN_NETWORK_TESTS=1 python3 -m pytest -m "network and web" -v
"""

from __future__ import annotations

import os

import pytest

pytestmark = [pytest.mark.web, pytest.mark.integration, pytest.mark.network]

_RUN_NETWORK = os.environ.get("RUN_NETWORK_TESTS", "").strip() == "1"
_SKIP_REASON = (
    "Live network test — set RUN_NETWORK_TESTS=1 to run. "
    "Requires ddgs, requests, trafilatura."
)


@pytest.mark.skipif(not _RUN_NETWORK, reason=_SKIP_REASON)
class TestLiveDuckDuckGoSearch:
    def test_returns_web_search_result(self) -> None:
        from research_core.adapters.web import WebSearchAdapter
        from research_core.protocols.web import WebSearchRequest, WebSearchResult
        from tests.conftest import make_research_request

        adapter = WebSearchAdapter(timeout_seconds=20.0)
        request = WebSearchRequest(
            query="Python packaging PEP 517",
            parent_request=make_research_request(max_web_results=3, max_web_pages=2),
        )
        result = adapter.search(request)
        assert isinstance(result, WebSearchResult)

    def test_sources_are_source_objects(self) -> None:
        from research_core.adapters.web import WebSearchAdapter
        from research_core.contracts.sources import Source
        from research_core.protocols.web import WebSearchRequest
        from tests.conftest import make_research_request

        adapter = WebSearchAdapter(timeout_seconds=20.0)
        request = WebSearchRequest(
            query="Python packaging PEP 517",
            parent_request=make_research_request(max_web_results=3, max_web_pages=2),
        )
        result = adapter.search(request)
        for src in result.sources:
            assert isinstance(src, Source)

    def test_source_type_is_web(self) -> None:
        from research_core.adapters.web import WebSearchAdapter
        from research_core.contracts.common import SourceType
        from research_core.protocols.web import WebSearchRequest
        from tests.conftest import make_research_request

        adapter = WebSearchAdapter(timeout_seconds=20.0)
        request = WebSearchRequest(
            query="Python packaging PEP 517",
            parent_request=make_research_request(max_web_results=3, max_web_pages=2),
        )
        result = adapter.search(request)
        for src in result.sources:
            assert src.source_type == SourceType.WEB

    def test_evidence_source_references_resolve(self) -> None:
        from research_core.adapters.web import WebSearchAdapter
        from research_core.protocols.web import WebSearchRequest
        from tests.conftest import make_research_request

        adapter = WebSearchAdapter(timeout_seconds=20.0)
        request = WebSearchRequest(
            query="Python packaging PEP 517",
            parent_request=make_research_request(max_web_results=3, max_web_pages=2),
        )
        result = adapter.search(request)
        source_ids = {s.source_id for s in result.sources}
        for ev in result.evidence:
            assert ev.source_id in source_ids

    def test_retrieved_at_timezone_aware(self) -> None:
        from research_core.adapters.web import WebSearchAdapter
        from research_core.protocols.web import WebSearchRequest
        from tests.conftest import make_research_request

        adapter = WebSearchAdapter(timeout_seconds=20.0)
        request = WebSearchRequest(
            query="Python packaging PEP 517",
            parent_request=make_research_request(max_web_results=3, max_web_pages=2),
        )
        result = adapter.search(request)
        for ev in result.evidence:
            assert ev.provenance.retrieved_at.tzinfo is not None

    def test_provider_identity_is_duckduckgo(self) -> None:
        from research_core.adapters.web import WebSearchAdapter
        from research_core.protocols.web import WebSearchRequest
        from tests.conftest import make_research_request

        adapter = WebSearchAdapter(timeout_seconds=20.0)
        request = WebSearchRequest(
            query="Python packaging PEP 517",
            parent_request=make_research_request(max_web_results=3, max_web_pages=2),
        )
        result = adapter.search(request)
        for ev in result.evidence:
            assert ev.provenance.provider == "duckduckgo"

    def test_claim_links_empty(self) -> None:
        from research_core.adapters.web import WebSearchAdapter
        from research_core.protocols.web import WebSearchRequest
        from tests.conftest import make_research_request

        adapter = WebSearchAdapter(timeout_seconds=20.0)
        request = WebSearchRequest(
            query="Python packaging PEP 517",
            parent_request=make_research_request(max_web_results=3, max_web_pages=2),
        )
        result = adapter.search(request)
        for ev in result.evidence:
            assert ev.claim_links == ()

    def test_no_quality_scores_fabricated(self) -> None:
        from research_core.adapters.web import WebSearchAdapter
        from research_core.protocols.web import WebSearchRequest
        from tests.conftest import make_research_request

        adapter = WebSearchAdapter(timeout_seconds=20.0)
        request = WebSearchRequest(
            query="Python packaging PEP 517",
            parent_request=make_research_request(max_web_results=3, max_web_pages=2),
        )
        result = adapter.search(request)
        for ev in result.evidence:
            assert ev.quality.authority is None
            assert ev.quality.extraction_confidence is None

    def test_result_serializable(self) -> None:
        import json

        from research_core.adapters.web import WebSearchAdapter
        from research_core.contracts.serialization import serialize
        from research_core.protocols.web import WebSearchRequest
        from tests.conftest import make_research_request

        adapter = WebSearchAdapter(timeout_seconds=20.0)
        request = WebSearchRequest(
            query="Python packaging PEP 517",
            parent_request=make_research_request(max_web_results=3, max_web_pages=2),
        )
        result = adapter.search(request)
        serialized = serialize(result)
        json.dumps(serialized)
