"""Tests for WebSearchAdapter — unit tests with injected fakes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.web

from research_core.adapters.web.adapter import WebSearchAdapter  # noqa: E402
from research_core.adapters.web.models import (  # noqa: E402
    ExtractionResult,
    FetchedResource,
    SearchHit,
)
from research_core.contracts.common import SourceType  # noqa: E402
from research_core.exceptions import ProviderExecutionError, ProviderUnavailableError  # noqa: E402
from research_core.protocols.web import WebSearchRequest, WebSearchResult  # noqa: E402
from tests.conftest import make_research_request  # noqa: E402

from .conftest import (  # noqa: E402
    make_extraction_result,
    make_fetched_resource,
    make_search_hit,
)


def _make_request(**kwargs: object) -> WebSearchRequest:
    max_results = kwargs.pop("max_results", 5)
    max_pages = kwargs.pop("max_pages", 5)
    parent = make_research_request(max_web_results=max_results, max_web_pages=max_pages)  # type: ignore[arg-type]
    return WebSearchRequest(
        query=str(kwargs.pop("query", "test query")),
        parent_request=parent,
        **kwargs,  # type: ignore[arg-type]
    )


def _make_search_client(hits: tuple[SearchHit, ...]) -> MagicMock:
    client = MagicMock()
    client.search.return_value = hits
    return client


def _make_fetcher(resource: FetchedResource) -> MagicMock:
    fetcher = MagicMock()
    fetcher.fetch.return_value = resource
    return fetcher


def _make_extractor(extraction: ExtractionResult) -> MagicMock:
    extractor = MagicMock()
    extractor.can_extract.return_value = True
    extractor.extract.return_value = extraction
    return extractor


class TestWebSearchAdapterConstruction:
    def test_construction_requires_no_deps(self) -> None:
        adapter = WebSearchAdapter()
        assert adapter is not None

    def test_default_timeout(self) -> None:
        adapter = WebSearchAdapter()
        assert adapter._timeout_seconds == 20.0

    def test_custom_timeout(self) -> None:
        adapter = WebSearchAdapter(timeout_seconds=5.0)
        assert adapter._timeout_seconds == 5.0

    def test_cache_none_by_default(self) -> None:
        adapter = WebSearchAdapter()
        assert adapter._cache is None

    def test_is_available_returns_bool(self) -> None:
        result = WebSearchAdapter.is_available()
        assert isinstance(result, bool)


class TestWebSearchAdapterSearchSuccess:
    def test_returns_web_search_result(self) -> None:
        hits = (make_search_hit(url="https://example.com/a"),)
        resource = make_fetched_resource()
        extraction = make_extraction_result()

        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=_make_fetcher(resource),
            extractor=_make_extractor(extraction),
        )
        result = adapter.search(_make_request())
        assert isinstance(result, WebSearchResult)

    def test_empty_search_hits_returns_empty_result(self) -> None:
        adapter = WebSearchAdapter(
            search_client=_make_search_client(()),
            page_fetcher=MagicMock(),
            extractor=MagicMock(),
        )
        result = adapter.search(_make_request())
        assert result.sources == ()
        assert result.evidence == ()

    def test_source_type_is_web(self) -> None:
        hits = (make_search_hit(),)
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=_make_fetcher(resource),
            extractor=_make_extractor(extraction),
        )
        result = adapter.search(_make_request())
        assert len(result.sources) == 1
        assert result.sources[0].source_type == SourceType.WEB

    def test_source_reference_resolves(self) -> None:
        hits = (make_search_hit(url="https://example.com/page"),)
        resource = make_fetched_resource(final_url="https://example.com/page")
        extraction = make_extraction_result()
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=_make_fetcher(resource),
            extractor=_make_extractor(extraction),
        )
        result = adapter.search(_make_request())
        assert len(result.evidence) == 1
        ev = result.evidence[0]
        source_ids = {s.source_id for s in result.sources}
        assert ev.source_id in source_ids

    def test_claim_links_empty(self) -> None:
        hits = (make_search_hit(),)
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=_make_fetcher(make_fetched_resource()),
            extractor=_make_extractor(make_extraction_result()),
        )
        result = adapter.search(_make_request())
        assert all(ev.claim_links == () for ev in result.evidence)

    def test_retrieval_rank_preserved(self) -> None:
        hits = (make_search_hit(rank=2, url="https://example.com/b"),)
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=_make_fetcher(resource),
            extractor=_make_extractor(extraction),
        )
        result = adapter.search(_make_request())
        assert result.evidence[0].provenance.retrieval_rank == 2

    def test_retrieval_score_is_none(self) -> None:
        hits = (make_search_hit(),)
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=_make_fetcher(make_fetched_resource()),
            extractor=_make_extractor(make_extraction_result()),
        )
        result = adapter.search(_make_request())
        assert result.evidence[0].provenance.retrieval_score is None

    def test_no_quality_scores_fabricated(self) -> None:
        hits = (make_search_hit(),)
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=_make_fetcher(make_fetched_resource()),
            extractor=_make_extractor(make_extraction_result()),
        )
        result = adapter.search(_make_request())
        q = result.evidence[0].quality
        assert q.authority is None
        assert q.relevance is None
        assert q.recency is None
        assert q.extraction_confidence is None

    def test_max_pages_limits_fetches(self) -> None:
        hits = tuple(
            make_search_hit(rank=i + 1, url=f"https://example.com/page{i}")
            for i in range(10)
        )
        fetcher = MagicMock()
        fetcher.fetch.return_value = make_fetched_resource()
        extractor = _make_extractor(make_extraction_result())

        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=fetcher,
            extractor=extractor,
        )
        adapter.search(_make_request(max_results=10, max_pages=3))
        assert fetcher.fetch.call_count <= 3

    def test_query_passed_to_search_client(self) -> None:
        client = _make_search_client(())
        adapter = WebSearchAdapter(
            search_client=client,
            page_fetcher=MagicMock(),
            extractor=MagicMock(),
        )
        adapter.search(_make_request(query="nuclear energy"))
        call_kwargs = client.search.call_args.kwargs
        assert call_kwargs["query"] == "nuclear energy"


class TestWebSearchAdapterDiagnostics:
    def test_result_metadata_has_pages_attempted(self) -> None:
        hits = (make_search_hit(url="https://example.com/page"),)
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=_make_fetcher(make_fetched_resource()),
            extractor=_make_extractor(make_extraction_result()),
        )
        result = adapter.search(_make_request())
        assert "pages_attempted" in result.metadata
        assert result.metadata["pages_attempted"] == 1

    def test_result_metadata_has_search_hits(self) -> None:
        hits = (make_search_hit(url="https://example.com/a"), make_search_hit(url="https://example.com/b"))
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=_make_fetcher(make_fetched_resource()),
            extractor=_make_extractor(make_extraction_result()),
        )
        result = adapter.search(_make_request(max_pages=5))
        assert result.metadata["search_hits"] == 2

    def test_all_page_failure_distinguishable_from_zero_hits(self) -> None:
        """Zero hits: pages_attempted=0. All-page failure: pages_attempted>0, pages_succeeded=0."""
        # Zero hits case
        zero_result = WebSearchAdapter(
            search_client=_make_search_client(()),
            page_fetcher=MagicMock(),
            extractor=MagicMock(),
        ).search(_make_request())
        assert zero_result.metadata["pages_attempted"] == 0
        assert zero_result.metadata["search_hits"] == 0

        # All-page failure case
        fetcher = MagicMock()
        fetcher.fetch.side_effect = ProviderExecutionError("fetch failed")
        all_fail_result = WebSearchAdapter(
            search_client=_make_search_client((make_search_hit(url="https://example.com/x"),)),
            page_fetcher=fetcher,
            extractor=MagicMock(),
        ).search(_make_request())
        assert all_fail_result.metadata["search_hits"] == 1
        assert all_fail_result.metadata["pages_attempted"] == 1
        assert all_fail_result.metadata["pages_succeeded"] == 0
        assert all_fail_result.evidence == ()


class TestWebSearchAdapterPartialFailures:
    def test_one_page_failure_skipped(self) -> None:
        hits = (
            make_search_hit(rank=1, url="https://example.com/a"),
            make_search_hit(rank=2, url="https://example.com/b"),
        )
        fetcher = MagicMock()
        good_resource = make_fetched_resource(final_url="https://example.com/b")
        bad_exc = ProviderExecutionError("fetch failed")
        fetcher.fetch.side_effect = [bad_exc, good_resource]

        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=fetcher,
            extractor=_make_extractor(make_extraction_result()),
        )
        result = adapter.search(_make_request())
        assert len(result.evidence) == 1

    def test_http_error_page_skipped(self) -> None:
        hits = (make_search_hit(),)
        resource = make_fetched_resource(status_code=404)
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=_make_fetcher(resource),
            extractor=MagicMock(),
        )
        result = adapter.search(_make_request())
        assert result.evidence == ()

    def test_extraction_failure_skipped(self) -> None:
        hits = (
            make_search_hit(rank=1, url="https://example.com/a"),
            make_search_hit(rank=2, url="https://example.com/b"),
        )
        fetcher = MagicMock()
        fetcher.fetch.return_value = make_fetched_resource()
        extractor = MagicMock()
        extractor.can_extract.return_value = True
        good_result = make_extraction_result()
        extractor.extract.side_effect = [
            ProviderExecutionError("extraction failed"),
            good_result,
        ]
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=fetcher,
            extractor=extractor,
        )
        result = adapter.search(_make_request())
        assert len(result.evidence) == 1

    def test_total_search_failure_raises(self) -> None:
        client = MagicMock()
        client.search.side_effect = ProviderExecutionError("search down")
        adapter = WebSearchAdapter(search_client=client)
        with pytest.raises(ProviderExecutionError):
            adapter.search(_make_request())

    def test_search_unavailable_raises(self) -> None:
        client = MagicMock()
        client.search.side_effect = ProviderUnavailableError("no ddgs")
        adapter = WebSearchAdapter(search_client=client)
        with pytest.raises(ProviderUnavailableError):
            adapter.search(_make_request())


class TestWebSearchAdapterDeduplication:
    def test_duplicate_urls_deduplicated(self) -> None:
        hits = (
            make_search_hit(rank=1, url="https://example.com/page"),
            make_search_hit(rank=2, url="https://example.com/page"),
        )
        fetcher = MagicMock()
        fetcher.fetch.return_value = make_fetched_resource()
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=fetcher,
            extractor=_make_extractor(make_extraction_result()),
        )
        adapter.search(_make_request())
        assert fetcher.fetch.call_count == 1

    def test_sources_deduplicated(self) -> None:
        hits = (
            make_search_hit(rank=1, url="https://example.com/page"),
            make_search_hit(rank=2, url="https://example.com/page"),
        )
        fetcher = MagicMock()
        fetcher.fetch.return_value = make_fetched_resource(final_url="https://example.com/page")
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=fetcher,
            extractor=_make_extractor(make_extraction_result()),
        )
        result = adapter.search(_make_request(max_pages=2))
        assert len(result.sources) == 1

    def test_invalid_scheme_url_skipped(self) -> None:
        hits = (
            make_search_hit(rank=1, url="javascript:void(0)"),
            make_search_hit(rank=2, url="https://example.com/valid"),
        )
        fetcher = MagicMock()
        fetcher.fetch.return_value = make_fetched_resource()
        adapter = WebSearchAdapter(
            search_client=_make_search_client(hits),
            page_fetcher=fetcher,
            extractor=_make_extractor(make_extraction_result()),
        )
        adapter.search(_make_request())
        first_call_url = fetcher.fetch.call_args_list[0][0][0]
        assert first_call_url != "javascript:void(0)"
