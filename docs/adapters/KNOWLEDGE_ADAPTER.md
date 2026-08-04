# Knowledge Adapter

**Status:** RC2 — production adapter  
**Protocol:** `KnowledgeProvider`  
**Backend:** `knowledge` package (`dc-power-agent`)

---

## Overview

`KnowledgeAdapter` is the production implementation of the `KnowledgeProvider` protocol. It connects `research-core` to the knowledge-layer (`dc-power-agent`), a JSONL-backed document store supporting lexical, semantic, and hybrid retrieval.

The adapter is located at `research_core.adapters.knowledge` and implements the `KnowledgeProvider` protocol defined in `research_core.protocols.knowledge`.

---

## Design Decisions

### Option A: KnowledgeRetrievalResult (RC1 contract correction)

RC1 defined `KnowledgeProvider.retrieve()` to return `tuple[EvidenceItem, ...]`. This was identified as a contract defect in RC2: downstream consumers assembling a `ResearchResult` need `Source` objects alongside evidence, and there was no reliable way to obtain them without a second lookup.

RC2 corrects this with **Option A** — the return type is now:

```python
@dataclass(frozen=True)
class KnowledgeRetrievalResult:
    sources: tuple[Source, ...]
    evidence: tuple[EvidenceItem, ...]
    metadata: Metadata
```

Both `sources` and `evidence` are returned in a single call. Sources are deduplicated by `source_id`.

### Lazy dependency import

The `knowledge` package is an optional dependency. The adapter module is importable and `KnowledgeAdapter` is constructable without the package installed. The `knowledge` import is deferred to the first `retrieve()` call. Attempting to retrieve when the package is absent raises `ProviderUnavailableError`.

Use `KnowledgeAdapter.is_available()` to probe at runtime.

### Multi-profile retrieval

The knowledge-layer retriever accepts a single `profile: str | None` argument per call. When `KnowledgeRetrievalRequest.profiles` contains multiple entries, the adapter issues one retrieval call per profile and merges results:

1. Retrieve separately for each profile with the full `top_k` budget.
2. Deduplicate by `evidence_id` — the highest-scoring version of each item is kept.
3. Re-sort the merged set by score (descending) and truncate to `top_k`.
4. Re-rank (assign sequential ranks 1…N).

### Score normalization

The knowledge-layer lexical retriever produces scores outside `[0, 1]`. The maximum theoretical score is:

```
lex_relevance_max   = 1.0 (term coverage) + 0.45 (intent boost) = 1.45
metadata_factor_max = quality(1.2) × priority(1.1) × strategic(1.1) ≈ 1.452
max_score           = 1.45 × 1.452 ≈ 2.1054
```

Scores are normalized by dividing by `2.1054` and clipping to `[0.0, 1.0]`. This preserves relative ordering while satisfying the research-core contract that `Provenance.retrieval_score ∈ [0.0, 1.0]`.

### Quality mapping

`KnowledgeMetadata` uses a 1–5 scale for `relevance_score`, `source_quality_score`, and `specificity_score`. These are normalized linearly to `[0.0, 1.0]` using `(score - 1.0) / 4.0`. `KnowledgeMetadata.confidence` is already in `[0.0, 1.0]` and maps directly to `EvidenceQuality.extraction_confidence`.

---

## Source Mapping

| Knowledge Layer `Source` field | research-core `Source` field | Notes |
|-------------------------------|------------------------------|-------|
| `source_id` | `source_id` | SHA-256[:32] fingerprint |
| `uri` | `url` | |
| `title` | `title` | |
| `author` | `author` | |
| `publisher` | `publisher` | |
| `publication_date` | `publication_date` | |
| `retrieved_date` (date) | `retrieved_at` (datetime) | Promoted to midnight UTC |
| `document_type` | `metadata["document_type"]` | No direct counterpart |
| `domain` | `metadata["domain"]` | |
| `subtitle` | `metadata["subtitle"]` | |
| `organization` | `metadata["organization"]` | |
| `copyright` | `metadata["copyright"]` | |
| `document_version` | `metadata["document_version"]` | |
| `document_number` | `metadata["document_number"]` | |
| `page_count` | `metadata["page_count"]` | |

All mapped sources use `SourceType.KNOWLEDGE`.

---

## Evidence Mapping

| Knowledge Layer `Evidence` / `RetrievedEvidence` | research-core `EvidenceItem` |
|--------------------------------------------------|------------------------------|
| `evidence.evidence_id` | `evidence_id` |
| `evidence.statement` | `content` |
| `evidence.supporting_source_ids[0]` | `source_id` (fallback: `evidence_id`) |
| `evidence.page_number` | `locator` ("page N") |
| `evidence.evidence_type` | `metadata["evidence_type"]` |
| `evidence.entity` | `metadata["entity"]` |
| `evidence.category` | `metadata["category"]` |
| `evidence.topics` | `metadata["topics"]` |
| `evidence.chunk_id` | `metadata["chunk_id"]` |
| `item.source_domain` | `metadata["source_domain"]` |
| `item.rank` | `provenance.retrieval_rank` |
| `normalize_score(item.score)` | `provenance.retrieval_score` |
| `evidence.content_fingerprint` | `provenance.content_hash` |

---

## Usage

```python
from research_core.adapters.knowledge import KnowledgeAdapter
from research_core.protocols.knowledge import KnowledgeRetrievalRequest
from research_core.contracts.request import ResearchRequest

# Check availability
if not KnowledgeAdapter.is_available():
    raise RuntimeError("Install research-core[knowledge] to use KnowledgeAdapter")

# Initialize
adapter = KnowledgeAdapter(
    store_root="/path/to/knowledge_store",
    load_sources=True,  # include Source records in the result
)

# Build a request
request = ResearchRequest(question="What are the deployment barriers for SMRs?")
k_request = KnowledgeRetrievalRequest(
    query="SMR deployment barriers risks",
    parent_request=request,
    profiles=("smr-general",),  # optional profile filter
)

# Retrieve
result = adapter.retrieve(k_request)
print(f"Evidence: {len(result.evidence)} items")
print(f"Sources:  {len(result.sources)} records")
```

See `examples/knowledge_adapter_query.py` for a runnable example.

---

## Error Handling

| Exception | Condition |
|-----------|-----------|
| `ProviderUnavailableError` | `knowledge` package not installed |
| `ProviderUnavailableError` | `KnowledgeStore` cannot be opened (bad path, I/O error) |
| `ProviderExecutionError` | Unexpected failure during retrieval |

The adapter never swallows exceptions silently. Partial failures surface as `ProviderExecutionError` with the original query in the message.

---

## Installation

```bash
# Install research-core with the knowledge adapter backend
pip install research-core[knowledge]

# Or install the knowledge layer directly from source
pip install -e /path/to/knowledge-layer
```

---

## Files

```
src/research_core/adapters/
  __init__.py                        — adapter package root
  knowledge/
    __init__.py                      — re-exports KnowledgeAdapter
    adapter.py                       — KnowledgeAdapter implementation
    mapping.py                       — type mapping and score normalization

tests/adapters/knowledge/
  conftest.py                        — shared fixtures (knowledge-layer objects)
  test_mapping.py                    — unit tests for mapping functions
  test_adapter.py                    — unit tests with mock retriever
  test_profiles.py                   — multi-profile merge and dedup tests
  test_exceptions.py                 — error handling tests
  test_optional_dependency.py        — lazy import contract tests
  test_integration.py                — integration tests (requires knowledge_store)

examples/
  knowledge_adapter_query.py         — runnable example script

docs/adapters/
  KNOWLEDGE_ADAPTER.md               — this document
```
