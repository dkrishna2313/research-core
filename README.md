# research-core

**Status: RC4 — Evidence Normalization and Ranking**

`research-core` is a domain-neutral Python research library. It provides a structured pipeline from a research question through knowledge retrieval, evidence ranking, claim analysis, contradiction detection, gap identification, and synthesis to a structured result.

RC4 delivers the `research_core.normalization` package: provider-neutral evidence normalization, deterministic segmentation of long documents, exact and near-duplicate detection, and multi-component ranking with full explainability. It also hardens the web fetcher against SSRF with per-hop redirect validation. The research engine is not yet implemented. All domain contracts, the knowledge adapter, the web search adapter, and the normalization layer are stable and importable.

---

## Architectural Positioning

```text
knowledge-layer
      ↓
research-core          ← this package
      ↓
consumer application
```

`research-core` is a library, not a report generator. Its canonical output is a structured `ResearchResult`. Markdown and other human-readable formats are optional renderer outputs derived from that structure.

`research-core` does not depend on — and must never import from — strategy layers, editorial layers, decision models, recommendation agents, or domain-specific consumer applications.

---

## Intended Conceptual Flow

```text
ResearchRequest
  → Knowledge retrieval     (provider boundary)
  → Optional web acquisition (provider boundary)
  → Source normalization
  → Evidence ranking
  → Claim extraction
  → Contradiction detection
  → Research gap analysis
  → Synthesis
  → ResearchResult
```

The contract layer is fully defined. Both the knowledge adapter and the web search adapter are live:

```python
from research_core.adapters.knowledge import KnowledgeAdapter
from research_core.protocols.knowledge import KnowledgeRetrievalRequest
from research_core import ResearchRequest

adapter = KnowledgeAdapter(store_root="/path/to/knowledge_store")
request = ResearchRequest(question="What are the deployment risks for SMRs?")
k_request = KnowledgeRetrievalRequest(
    query="SMR deployment barriers licensing",
    parent_request=request,
    profiles=("smr-general",),
)
result = adapter.retrieve(k_request)
print(f"Evidence: {len(result.evidence)} items")
```

```python
from research_core.adapters.web import WebSearchAdapter
from research_core.protocols.web import WebSearchRequest
from research_core import ResearchRequest

adapter = WebSearchAdapter()
request = ResearchRequest(question="What are the deployment risks for SMRs?")
w_request = WebSearchRequest(
    query="SMR deployment barriers licensing",
    parent_request=request,
)
result = adapter.search(w_request)
print(f"Evidence: {len(result.evidence)} items")
```

Future public API direction (RC8+):

```python
from research_core import ResearchEngine, ResearchRequest

engine = ResearchEngine(
    knowledge_provider=MyKnowledgeStore(),
    profile_provider=MyProfileRegistry(),
    synthesizer=MyLLMSynthesizer(),
)

result = engine.run(request)
```

The structured result exposes: `sources`, `evidence`, `claims`, `contradictions`,
`gaps`, `open_questions`, `synthesis`, `quality`, `trace`.

---

## Current Phase

**RC3 — Web Search Adapter**

This phase delivers:

- `src/research_core/adapters/web/` — `WebSearchAdapter`, `WebCache`, extractors, fetch, search, mapping
- `WebSearchResult` (RC3 contract correction) — bundles sources + evidence, same pattern as RC2
- DuckDuckGo search via `ddgs` or `duckduckgo_search` (lazy import)
- Page fetching via `requests` with 10 MB limit and streaming (lazy import)
- Content extraction pipeline: `trafilatura` (HTML), `pypdf` (PDF), `python-docx` (DOCX), plaintext fallback
- Optional disk cache with atomic writes and base64 for bytes fields
- `research-core[web]` optional dependency group
- 481 passing tests (490 collected, 9 skipped — network-gated), zero mypy errors, zero ruff violations

**RC2 deliverables** (still present):

- `src/research_core/adapters/knowledge/` — `KnowledgeAdapter` and type mapping
- `KnowledgeRetrievalResult` (RC1 contract correction) — bundles sources + evidence
- Score normalization from knowledge-layer `[0, ~2.1]` to `[0.0, 1.0]`
- Multi-profile retrieval with deduplication and re-ranking
- Lazy optional dependency: importable without `knowledge` installed

**RC1 deliverables** (still present):

- `src/research_core/contracts/` — all typed domain contracts (frozen dataclasses)
- `src/research_core/protocols/` — provider protocol boundaries (structural protocols)
- `src/research_core/exceptions.py` — typed exception hierarchy
- `docs/architecture/CONTRACTS.md` — contract reference documentation

**RC0 deliverables** (still present):

- `docs/product/PRODUCT_BRIEF.md` — users, use cases, non-goals, success criteria
- `docs/architecture/ARCHITECTURE.md` — component model, pipeline, boundaries
- `docs/architecture/DEPENDENCY_RULES.md` — enforceable dependency rules
- `docs/architecture/ROADMAP.md` — RC0 through RC9 with acceptance criteria

---

## Installation

The package is not yet released. For development setup:

```zsh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

Requires Python 3.11 or later. See `docs/architecture/ARCHITECTURE.md` for the rationale
behind this version floor.

---

## Development

```zsh
# Run tests
python3 -m pytest

# Lint
python3 -m ruff check .

# Type check
python3 -m mypy src
```

---

## Documentation

| Document | Purpose |
|---|---|
| [Product Brief](docs/product/PRODUCT_BRIEF.md) | Users, use cases, non-goals, risks |
| [Architecture](docs/architecture/ARCHITECTURE.md) | Pipeline, components, boundaries |
| [Contracts Reference](docs/architecture/CONTRACTS.md) | Contract types, validation, serialization |
| [Dependency Rules](docs/architecture/DEPENDENCY_RULES.md) | Enforceable import constraints |
| [Roadmap](docs/architecture/ROADMAP.md) | RC0–RC9 phases and acceptance criteria |
| [Knowledge Adapter](docs/adapters/KNOWLEDGE_ADAPTER.md) | Adapter design, mappings, usage |
| [Web Search Adapter](docs/adapters/WEB_SEARCH_ADAPTER.md) | Web adapter design, extractors, caching |

---

## Non-Goals

`research-core` does not and will not:

- Generate strategy, recommendations, or decisions
- Produce domain-specific report sections (power implications, rack architecture, etc.)
- Depend on editorial, delivery, or CMS layers
- Replace or wrap the legacy `research_agent` CLI wholesale
- Import from `functional_agents`, `strategy`, `editorial`, or `deliverables`
- Silently substitute a default profile when the requested profile is absent

---

## Roadmap Summary

| Phase | Description |
|---|---|
| RC0 | Product and Architecture Foundation ✓ |
| RC1 | Core Contracts and Package Boundary ✓ |
| RC2 | Knowledge Adapter ✓ |
| RC3 | Web Search Adapter ← current |
| RC4 | Evidence Normalization and Ranking |
| RC5 | Claim Extraction and Contradiction Detection |
| RC6 | Research Gap Analysis and Quality Diagnostics |
| RC7 | Synthesis and Renderers |
| RC8 | Standalone CLI and External Consumer Demo |
| RC9 | Legacy Component Migration |

---

## License

License: To be determined. Decision required before RC8.
