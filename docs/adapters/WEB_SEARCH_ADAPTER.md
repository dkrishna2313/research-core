# Web Search Adapter

**Status:** RC3 — production adapter  
**Protocol:** `WebSearchProvider`  
**Backend:** DuckDuckGo (`ddgs` or `duckduckgo_search`), `requests`, `trafilatura`, `pypdf`, `python-docx`

---

## Overview

`WebSearchAdapter` is the production implementation of the `WebSearchProvider` protocol. It searches the web via DuckDuckGo, fetches pages using `requests`, and extracts text using a pipeline of content extractors (`trafilatura` for HTML, `pypdf` for PDF, `python-docx` for DOCX, and plain-text fallback).

The adapter is located at `research_core.adapters.web` and implements the `WebSearchProvider` protocol defined in `research_core.protocols.web`.

---

## Design Decisions

### WebSearchResult (RC3 contract correction)

RC1 defined `WebSearchProvider.search()` to return `tuple[tuple[Source, EvidenceItem], ...]`. This was identified as a protocol defect in RC3 — the same class of defect corrected for knowledge in RC2.

RC3 corrects this with `WebSearchResult`:

```python
@dataclass(frozen=True)
class WebSearchResult:
    sources: tuple[Source, ...]
    evidence: tuple[EvidenceItem, ...]
    metadata: Metadata
```

Both `sources` and `evidence` are returned in a single call. Sources are deduplicated by `source_id`.

### Lazy optional dependencies

All web packages (`ddgs`, `requests`, `trafilatura`, `pypdf`, `python-docx`) are optional dependencies. The adapter module is importable and `WebSearchAdapter` is constructable without any of them installed. Each package is imported lazily — inside the method that uses it — so base-package import has zero optional overhead.

Attempting to search when `ddgs`/`duckduckgo_search` is absent raises `ProviderUnavailableError`. Attempting to fetch when `requests` is absent raises `ProviderExecutionError`. Attempting to extract when a specific extractor's dependency is absent raises `ProviderExecutionError` for that page (but does not abort the search).

Use `WebSearchAdapter.is_available()` to probe at runtime.

Install with:

```zsh
pip install "research-core[web]"
```

### Dependency injection

`WebSearchAdapter.__init__` accepts three injectable boundaries:

| Parameter | Protocol | Default |
|---|---|---|
| `search_client` | `SearchClient` | `DdgsSearchClient` (lazy ddgs import) |
| `page_fetcher` | `PageFetcher` | `RequestsFetcher` (lazy requests import) |
| `extractor` | `ContentExtractor` | `CompositeExtractor` pipeline |

The injected boundaries are `@runtime_checkable` structural protocols, not concrete types. Any compatible object — including `MagicMock` — satisfies the protocol for testing.

### Conservative evidence quality

All `EvidenceQuality` dimensions are `None` for web evidence:

| Dimension | Value | Reason |
|---|---|---|
| `relevance` | `None` | Not assessed — no reranker |
| `authority` | `None` | Not assessed — domain authority unavailable |
| `recency` | `None` | Not assessed — publication date rarely extractable |
| `extraction_confidence` | `None` | Not assessed — no confidence model |

No score is fabricated from HTTP status codes, search rank, or extraction success. RC4 introduces evidence ranking and quality scoring.

### Partial failure semantics

A single page failure (fetch error, extraction error, empty text, unsupported content type) is logged at DEBUG level and skipped. The search continues with remaining pages. The returned `WebSearchResult` contains only successfully processed pages.

Zero search results is not a failure — the adapter returns an empty `WebSearchResult`.

Total search-provider failure (DDGS unavailable, unexpected exception) raises `ProviderUnavailableError` or `ProviderExecutionError`.

### URL handling

- **Scheme validation**: `file://`, `javascript:`, `data:`, `ftp://`, `mailto:` are rejected before any network access. Only `http` and `https` are permitted.
- **URL normalization**: whitespace stripped, scheme and host lowercased, fragment removed, query parameters preserved.
- **Deduplication**: hits are deduplicated by normalized URL before fetching.
- **Deterministic IDs**: `source_id = "web-" + sha256(url)[:16]`, `evidence_id = "web-ev-" + sha256(url + "\x00" + content[:200])[:16]`.

### Response size limit

Responses are streamed with `iter_content(chunk_size=8192)` and truncated at 10 MB. A `truncated=True` flag is set on the `FetchedResource`. The truncated content is still processed normally.

### Optional disk cache

An optional `WebCache` can be supplied to `WebSearchAdapter(cache=WebCache(cache_dir))`. The cache:

- Keys by SHA-256 of the URL (16 hex chars).
- Stores data as JSON with base64 encoding for `bytes` fields.
- Uses atomic writes (`.tmp` + rename) to prevent corruption.
- Returns `None` on cache miss, deserialization error, or missing file.

---

## Content Extractor Pipeline

The default extractor (`default_extractor()`) is a `CompositeExtractor` that tries extractors in order, using the first matching one:

| Extractor | Content types | URL patterns | Dep |
|---|---|---|---|
| `PyPDFExtractor` | `application/pdf` | `*.pdf` | `pypdf` |
| `DocxExtractor` | `application/vnd.openxmlformats-*`, `application/msword` | `*.docx` | `python-docx` |
| `TrafilaturaExtractor` | `text/html`, `application/xhtml+xml`, `text/xml`, `text/*` | any | `trafilatura` |
| `PlainTextExtractor` | `text/plain` | any | (stdlib) |

If no extractor matches, `CompositeExtractor` raises `ProviderExecutionError("unsupported content type")`. Constructing the extractor pipeline does not import any optional dependency.

---

## Source Mapping

| Field | Source |
|---|---|
| `source_id` | `"web-" + sha256(url)[:16]` |
| `source_type` | `SourceType.WEB` |
| `url` | final URL (after redirects) |
| `title` | extracted title → search title → URL fallback |
| `publisher` | `None` (not assessed) |
| `author` | `None` (not assessed) |
| `publication_date` | `None` (not assessed) |
| `retrieved_at` | UTC timestamp at search call |
| `metadata["requested_url"]` | set only when redirected |
| `metadata["search_rank"]` | original DuckDuckGo rank |

---

## Usage

```python
from research_core.adapters.web import WebSearchAdapter
from research_core.protocols.web import WebSearchRequest
from research_core import ResearchRequest

if not WebSearchAdapter.is_available():
    print("Install: pip install research-core[web]")
    raise SystemExit(1)

parent = ResearchRequest(question="SMR deployment barriers")
request = WebSearchRequest(
    query="small modular reactor deployment barriers",
    parent_request=parent,
)

adapter = WebSearchAdapter()
result = adapter.search(request)

print(f"Sources:  {len(result.sources)}")
print(f"Evidence: {len(result.evidence)}")
for ev in result.evidence:
    print(f"  [{ev.provenance.retrieval_rank}] {ev.content[:80]}")
```

### With disk cache

```python
from pathlib import Path
from research_core.adapters.web import WebSearchAdapter
from research_core.adapters.web.cache import WebCache

cache = WebCache(Path(".cache/web"))
adapter = WebSearchAdapter(cache=cache)
result = adapter.search(request)
```

---

## Testing

Unit tests require no network access. All tests inject stub `search_client`, `page_fetcher`, and `extractor` objects. Integration tests are gated by `RUN_NETWORK_TESTS=1`:

```zsh
# Unit tests only (default)
python3 -m pytest tests/adapters/web/ -m web

# With live network
RUN_NETWORK_TESTS=1 python3 -m pytest tests/adapters/web/ -m "web and network"
```

---

## Thread Safety

`WebSearchAdapter` instances are not thread-safe. Each thread should use its own instance.
