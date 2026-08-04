"""
Mapping from web adapter internal models to research-core contracts.

Source IDs and evidence IDs are deterministic SHA-256 hashes of the URL
(and content prefix for evidence). This guarantees stability across runs
without requiring a centralized registry.

Quality mapping:
    EvidenceQuality is initialized with all dimensions as None. DDGS does not
    provide documented relevance scores; HTTP success and successful extraction
    are not factual confirmation; search rank does not indicate source authority.
    No quality dimensions are set by this adapter.

Provenance mapping:
    - provider: "duckduckgo" (the search provider identity)
    - retrieval_rank: search rank from DDGS result (1-based)
    - retrieval_score: None (DDGS does not provide a documented normalized score)
    - extraction_method: name of the extractor that produced the text
    - extraction_confidence: None (no semantic confidence from extractors)
    - content_hash: SHA-256 of the extracted text
"""

from __future__ import annotations

import hashlib
import types
from datetime import datetime
from urllib.parse import urldefrag, urlparse

from research_core.contracts.common import EMPTY_METADATA, SourceType
from research_core.contracts.evidence import EvidenceItem
from research_core.contracts.sources import EvidenceQuality, Provenance, Source
from research_core.exceptions import ProviderExecutionError

from .models import ExtractionResult, FetchedResource, SearchHit

_WEB_PROVIDER = "duckduckgo"


def source_id_for_url(url: str) -> str:
    """Deterministic source ID derived from the URL (without fragment)."""
    clean, _ = urldefrag(url)
    return "web-" + hashlib.sha256(clean.encode()).hexdigest()[:16]


def evidence_id_for(url: str, content: str) -> str:
    """Deterministic evidence ID derived from URL + first 200 chars of content."""
    clean, _ = urldefrag(url)
    key = f"{clean}\x00{content[:200]}"
    return "web-ev-" + hashlib.sha256(key.encode()).hexdigest()[:16]


def content_hash(text: str) -> str:
    """SHA-256 hex digest of the extracted text."""
    return hashlib.sha256(text.encode()).hexdigest()


def normalize_url(url: str) -> str:
    """Conservative URL normalization.

    - Strip leading/trailing whitespace
    - Lowercase scheme and host
    - Remove fragment
    - Preserve path, query parameters, and port

    Query parameters are preserved because they may identify document versions,
    pagination, language, or content pages.
    """
    url = url.strip()
    parsed = urlparse(url)
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment="",
    )
    return normalized.geturl()


def validate_scheme(url: str) -> None:
    """Raise ProviderExecutionError for non-http/https schemes."""
    scheme = urlparse(url).scheme.lower()
    if scheme not in {"http", "https"}:
        raise ProviderExecutionError(
            f"unsupported URL scheme {scheme!r} in {url!r}; "
            f"only http and https are permitted"
        )


def map_source(
    hit: SearchHit,
    resource: FetchedResource,
    extraction: ExtractionResult,
    retrieved_at: datetime,
) -> Source:
    """Map web fetch results to a research-core Source.

    Title precedence: extracted title → search hit title → final URL.
    Publisher and author are not set (not deterministically available from DDGS).
    Publication date is not set (not reliably provided by DDGS).
    """
    title = (
        (extraction.title or "").strip()
        or (hit.title or "").strip()
        or resource.final_url
    )
    src_id = source_id_for_url(resource.final_url)

    extra: dict[str, object] = {
        "content_type": resource.content_type,
        "status_code": resource.status_code,
    }
    if resource.requested_url != resource.final_url:
        extra["requested_url"] = resource.requested_url

    return Source(
        source_id=src_id,
        source_type=SourceType.WEB,
        title=title,
        url=resource.final_url,
        retrieved_at=retrieved_at,
        metadata=types.MappingProxyType(extra),
    )


def map_provenance(
    hit: SearchHit,
    resource: FetchedResource,
    extraction: ExtractionResult,
    text: str,
    query: str,
    retrieved_at: datetime,
) -> Provenance:
    """Map web fetch results to a research-core Provenance."""
    src_id = source_id_for_url(resource.final_url)

    meta: dict[str, object] = {"snippet": hit.snippet[:200]}
    if resource.requested_url != resource.final_url:
        meta["requested_url"] = resource.requested_url

    return Provenance(
        source_id=src_id,
        source_type=SourceType.WEB,
        retrieved_at=retrieved_at,
        url=resource.final_url,
        provider=_WEB_PROVIDER,
        retrieval_query=query,
        retrieval_rank=hit.rank,
        retrieval_score=None,
        extraction_method=extraction.extraction_method,
        extraction_confidence=None,
        content_hash=content_hash(text),
        metadata=types.MappingProxyType(meta),
    )


def map_evidence_item(
    hit: SearchHit,
    resource: FetchedResource,
    extraction: ExtractionResult,
    query: str,
    retrieved_at: datetime,
) -> EvidenceItem:
    """Map web fetch results to a research-core EvidenceItem.

    Raises ProviderExecutionError if the extracted text is empty.
    Quality dimensions are all None — see module docstring for rationale.
    """
    text = extraction.text.strip()
    if not text:
        raise ProviderExecutionError(
            f"empty extracted text for {resource.final_url!r}"
        )

    src_id = source_id_for_url(resource.final_url)
    ev_id = evidence_id_for(resource.final_url, text)
    provenance = map_provenance(hit, resource, extraction, text, query, retrieved_at)

    extra: dict[str, object] = {"extraction_method": extraction.extraction_method}
    if extraction.page_count is not None:
        extra["page_count"] = extraction.page_count
    if extraction.truncated:
        extra["truncated"] = True

    return EvidenceItem(
        evidence_id=ev_id,
        content=text,
        source_id=src_id,
        provenance=provenance,
        quality=EvidenceQuality(),
        claim_links=(),
        metadata=types.MappingProxyType(extra) if extra else EMPTY_METADATA,
    )
