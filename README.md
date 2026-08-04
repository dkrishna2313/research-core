# research-core

**Status: RC0 — Product and Architecture Foundation**

`research-core` is a domain-neutral Python research library. It provides a structured pipeline from a research question through knowledge retrieval, evidence ranking, claim analysis, contradiction detection, gap identification, and synthesis to a structured result.

The research engine is not yet implemented. This release establishes the product definition, architecture, dependency rules, and development tooling only.

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

Future public API direction:

```python
from research_core import ResearchEngine, ResearchRequest

engine = ResearchEngine(
    knowledge_store="/path/to/knowledge_store",
    web_provider="duckduckgo",
)

result = engine.run(
    ResearchRequest(
        question="What are the major growth opportunities in sports consulting?",
        profiles=["sports"],
        use_web=True,
        max_web_results=8,
    )
)
```

The structured result will expose: `summary`, `claims`, `evidence`, `contradictions`,
`research_gaps`, `open_questions`, `sources`, `quality_diagnostics`, `trace`.

---

## Current Phase

**RC0 — Product and Architecture Foundation**

This phase delivers:

- `docs/product/PRODUCT_BRIEF.md` — users, use cases, non-goals, success criteria
- `docs/architecture/ARCHITECTURE.md` — component model, pipeline, boundaries
- `docs/architecture/DEPENDENCY_RULES.md` — enforceable dependency rules
- `docs/architecture/ROADMAP.md` — RC0 through RC9 with acceptance criteria

No retrieval, web search, LLM calls, evidence ranking, claim extraction, contradiction detection,
gap analysis, synthesis, rendering, or research CLI is implemented in RC0.

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
| [Dependency Rules](docs/architecture/DEPENDENCY_RULES.md) | Enforceable import constraints |
| [Roadmap](docs/architecture/ROADMAP.md) | RC0–RC9 phases and acceptance criteria |

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
| RC0 | Product and Architecture Foundation ← current |
| RC1 | Core Contracts and Package Boundary |
| RC2 | Knowledge Adapter |
| RC3 | Web Search Adapter |
| RC4 | Evidence Normalization and Ranking |
| RC5 | Claim Extraction and Contradiction Detection |
| RC6 | Research Gap Analysis and Quality Diagnostics |
| RC7 | Synthesis and Renderers |
| RC8 | Standalone CLI and External Consumer Demo |
| RC9 | Legacy Component Migration |

---

## License

License: To be determined. Decision required before RC8.
