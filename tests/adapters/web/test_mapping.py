"""Tests for web adapter mapping functions."""

from __future__ import annotations

import hashlib

import pytest

pytestmark = pytest.mark.web

from research_core.adapters.web.mapping import (  # noqa: E402
    content_hash,
    evidence_id_for,
    map_evidence_item,
    map_provenance,
    map_source,
    normalize_url,
    source_id_for_url,
    validate_scheme,
)
from research_core.contracts.common import SourceType  # noqa: E402
from research_core.contracts.evidence import EvidenceItem  # noqa: E402
from research_core.contracts.sources import Source  # noqa: E402
from research_core.exceptions import ProviderExecutionError  # noqa: E402

from .conftest import (  # noqa: E402
    FIXED_TS,
    make_extraction_result,
    make_fetched_resource,
    make_search_hit,
)


class TestSourceIdForUrl:
    def test_deterministic(self) -> None:
        assert source_id_for_url("https://example.com") == source_id_for_url(
            "https://example.com"
        )

    def test_different_urls_different_ids(self) -> None:
        assert source_id_for_url("https://example.com/a") != source_id_for_url(
            "https://example.com/b"
        )

    def test_id_starts_with_web_prefix(self) -> None:
        assert source_id_for_url("https://example.com").startswith("web-")

    def test_fragment_ignored(self) -> None:
        assert source_id_for_url("https://example.com/page#section") == source_id_for_url(
            "https://example.com/page"
        )


class TestEvidenceIdFor:
    def test_deterministic(self) -> None:
        assert evidence_id_for("https://example.com", "text") == evidence_id_for(
            "https://example.com", "text"
        )

    def test_different_content_different_ids(self) -> None:
        assert evidence_id_for("https://example.com", "text A") != evidence_id_for(
            "https://example.com", "text B"
        )

    def test_id_starts_with_web_ev_prefix(self) -> None:
        assert evidence_id_for("https://example.com", "text").startswith("web-ev-")


class TestContentHash:
    def test_deterministic(self) -> None:
        assert content_hash("hello") == content_hash("hello")

    def test_sha256(self) -> None:
        expected = hashlib.sha256(b"hello").hexdigest()
        assert content_hash("hello") == expected


class TestNormalizeUrl:
    def test_strips_whitespace(self) -> None:
        assert normalize_url("  https://example.com  ") == "https://example.com"

    def test_lowercases_scheme(self) -> None:
        assert normalize_url("HTTPS://example.com").startswith("https://")

    def test_lowercases_host(self) -> None:
        assert "EXAMPLE.COM".lower() in normalize_url("https://EXAMPLE.COM").lower()

    def test_removes_fragment(self) -> None:
        assert "#section" not in normalize_url("https://example.com/page#section")

    def test_preserves_path(self) -> None:
        url = "https://example.com/path/to/page"
        assert "/path/to/page" in normalize_url(url)

    def test_preserves_query_params(self) -> None:
        url = "https://example.com/page?id=123&lang=en"
        normalized = normalize_url(url)
        assert "id=123" in normalized
        assert "lang=en" in normalized


class TestValidateScheme:
    def test_http_accepted(self) -> None:
        validate_scheme("http://example.com")  # no raise

    def test_https_accepted(self) -> None:
        validate_scheme("https://example.com")  # no raise

    def test_file_rejected(self) -> None:
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            validate_scheme("file:///etc/passwd")

    def test_javascript_rejected(self) -> None:
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            validate_scheme("javascript:void(0)")

    def test_data_rejected(self) -> None:
        with pytest.raises(ProviderExecutionError, match="unsupported URL scheme"):
            validate_scheme("data:text/html,hi")


class TestMapSource:
    def _map(self, **kwargs: object) -> Source:
        hit = make_search_hit(**{k: v for k, v in kwargs.items() if k in ("url", "title")})  # type: ignore[arg-type]
        resource = make_fetched_resource(
            **{k: v for k, v in kwargs.items() if k in ("final_url", "status_code", "content_type")}  # type: ignore[arg-type]
        )
        extraction = make_extraction_result(
            **{k: v for k, v in kwargs.items() if k in ("title",)}  # type: ignore[arg-type]
        )
        return map_source(hit, resource, extraction, FIXED_TS)

    def test_source_type_is_web(self) -> None:
        src = self._map()
        assert src.source_type == SourceType.WEB

    def test_source_id_is_stable(self) -> None:
        src1 = self._map()
        src2 = self._map()
        assert src1.source_id == src2.source_id

    def test_url_is_final_url(self) -> None:
        resource = make_fetched_resource(final_url="https://example.com/final")
        hit = make_search_hit()
        extraction = make_extraction_result()
        src = map_source(hit, resource, extraction, FIXED_TS)
        assert src.url == "https://example.com/final"

    def test_extracted_title_takes_precedence(self) -> None:
        hit = make_search_hit(title="Search Title")
        resource = make_fetched_resource()
        extraction = make_extraction_result(title="Extracted Title")
        src = map_source(hit, resource, extraction, FIXED_TS)
        assert src.title == "Extracted Title"

    def test_search_title_fallback(self) -> None:
        hit = make_search_hit(title="Search Title")
        resource = make_fetched_resource()
        extraction = make_extraction_result(title=None)
        src = map_source(hit, resource, extraction, FIXED_TS)
        assert src.title == "Search Title"

    def test_retrieved_at_preserved(self) -> None:
        src = self._map()
        assert src.retrieved_at == FIXED_TS

    def test_publisher_not_set(self) -> None:
        src = self._map()
        assert src.publisher is None

    def test_author_not_set(self) -> None:
        src = self._map()
        assert src.author is None

    def test_publication_date_not_set(self) -> None:
        src = self._map()
        assert src.publication_date is None

    def test_metadata_json_compatible(self) -> None:
        import json

        src = self._map()
        import types

        assert isinstance(src.metadata, types.MappingProxyType)
        json.dumps(dict(src.metadata))

    def test_requested_url_in_metadata_when_redirect(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource(
            requested_url="https://example.com/original",
            final_url="https://example.com/redirected",
        )
        extraction = make_extraction_result()
        src = map_source(hit, resource, extraction, FIXED_TS)
        assert src.metadata.get("requested_url") == "https://example.com/original"


class TestMapProvenance:
    def test_source_type_is_web(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        prov = map_provenance(hit, resource, extraction, "text", "query", FIXED_TS)
        assert prov.source_type == SourceType.WEB

    def test_provider_is_duckduckgo(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        prov = map_provenance(hit, resource, extraction, "text", "query", FIXED_TS)
        assert prov.provider == "duckduckgo"

    def test_retrieval_rank_preserved(self) -> None:
        hit = make_search_hit(rank=3)
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        prov = map_provenance(hit, resource, extraction, "text", "query", FIXED_TS)
        assert prov.retrieval_rank == 3

    def test_retrieval_score_is_none(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        prov = map_provenance(hit, resource, extraction, "text", "query", FIXED_TS)
        assert prov.retrieval_score is None

    def test_extraction_confidence_is_none(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        prov = map_provenance(hit, resource, extraction, "text", "query", FIXED_TS)
        assert prov.extraction_confidence is None

    def test_content_hash_is_deterministic(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        prov1 = map_provenance(hit, resource, extraction, "same text", "query", FIXED_TS)
        prov2 = map_provenance(hit, resource, extraction, "same text", "query", FIXED_TS)
        assert prov1.content_hash == prov2.content_hash

    def test_extraction_method_preserved(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result(method="pypdf")
        prov = map_provenance(hit, resource, extraction, "text", "query", FIXED_TS)
        assert prov.extraction_method == "pypdf"

    def test_retrieval_query_preserved(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        prov = map_provenance(hit, resource, extraction, "text", "my search query", FIXED_TS)
        assert prov.retrieval_query == "my search query"

    def test_retrieved_at_preserved(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        prov = map_provenance(hit, resource, extraction, "text", "query", FIXED_TS)
        assert prov.retrieved_at == FIXED_TS


class TestMapEvidenceItem:
    def test_returns_evidence_item(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        ev = map_evidence_item(hit, resource, extraction, "query", FIXED_TS)
        assert isinstance(ev, EvidenceItem)

    def test_content_is_extracted_text(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result(text="My extracted content here.")
        ev = map_evidence_item(hit, resource, extraction, "query", FIXED_TS)
        assert ev.content == "My extracted content here."

    def test_source_id_matches_source(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        ev = map_evidence_item(hit, resource, extraction, "query", FIXED_TS)
        src = map_source(hit, resource, extraction, FIXED_TS)
        assert ev.source_id == src.source_id

    def test_claim_links_empty(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        ev = map_evidence_item(hit, resource, extraction, "query", FIXED_TS)
        assert ev.claim_links == ()

    def test_quality_all_none(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        ev = map_evidence_item(hit, resource, extraction, "query", FIXED_TS)
        assert ev.quality.relevance is None
        assert ev.quality.authority is None
        assert ev.quality.recency is None
        assert ev.quality.extraction_confidence is None

    def test_evidence_id_stable(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        ev1 = map_evidence_item(hit, resource, extraction, "query", FIXED_TS)
        ev2 = map_evidence_item(hit, resource, extraction, "query", FIXED_TS)
        assert ev1.evidence_id == ev2.evidence_id

    def test_empty_content_raises(self) -> None:
        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result(text="   ")
        with pytest.raises(ProviderExecutionError, match="empty"):
            map_evidence_item(hit, resource, extraction, "query", FIXED_TS)

    def test_metadata_json_compatible(self) -> None:
        import json

        hit = make_search_hit()
        resource = make_fetched_resource()
        extraction = make_extraction_result()
        ev = map_evidence_item(hit, resource, extraction, "query", FIXED_TS)
        json.dumps(dict(ev.metadata))
