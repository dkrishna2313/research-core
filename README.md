# research-core

**Status: RC8.1.1 — Answer-Only CLI View**

`research-core` is a domain-neutral Python research library. It provides a structured pipeline from a research question through knowledge retrieval, evidence ranking, claim analysis, contradiction detection, gap identification, and synthesis to a structured result.

RC8.1 adds live Knowledge Layer execution via `--knowledge-store`. RC8.1.1 adds `--answer-only` for a concise synthesized answer view while still running the full research pipeline internally.

---

## Quick Start

```bash
pip install research-core

# Markdown output (default)
research-core run "What are the key drivers of Arctic sea ice decline?" --fixture

# JSON output
research-core run "Your question" --fixture --format json

# Answer-only view (synthesized answer, full pipeline still runs)
research-core run "What are the major trends shaping the sports industry?" \
    --knowledge-store /path/to/knowledge_store \
    --answer-only

# Via Python module
python -m research_core.cli run "Your question" --fixture
```

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

### Library usage

```python
from research_core.cli.providers import build_fixture_engine
from research_core.contracts.request import ResearchRequest
from research_core.renderers import MarkdownRenderer

engine = build_fixture_engine()
result = engine.run(ResearchRequest(question="Climate tipping points"))
print(MarkdownRenderer().render(result))
```

### Production usage (custom providers)

```python
from research_core import ResearchEngine, ResearchRequest

engine = ResearchEngine(
    knowledge_provider=MyKnowledgeStore(),
    profile_provider=MyProfileRegistry(),
    synthesizer=MyLLMSynthesizer(),
)
result = engine.run(request)
```

---

## CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `research-core run QUESTION [--fixture] [--format markdown\|json]` | Run a research pipeline |
| `research-core --version` | Print version |
| `research-core --help` | Show help |

### Options for `run`

| Flag | Default | Description |
|------|---------|-------------|
| `--format {markdown,json}` | `markdown` | Output format |
| `--fixture` | off | Use deterministic in-memory providers |
| `--profile PROFILE_ID` | `default` | Profile ID |
| `--web` | off | Enable web evidence |
| `--strict` | off | Fail on missing evidence |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success (COMPLETE or PARTIAL result) |
| `2` | Usage error |
| `3` | Blank or invalid question |
| `4` | Unknown profile |
| `5` | Provider failure |
| `6` | Pipeline execution failure |
| `7` | Output rendering failure |
| `8` | No providers configured (add `--fixture`) |

See [docs/cli/EXIT_CODES.md](docs/cli/EXIT_CODES.md) for full reference.

---

## Current Phase

**RC8 — Standalone CLI and External Consumer Demo**

This phase delivers:

- `research-core` console script (installable via `pip install research-core`)
- `research_core.cli` package — `app`, `parser`, `commands`, `output`, `providers`, `config`, `exit_codes`
- `research-core run` subcommand with `--format markdown|json`, `--fixture`, `--profile`, `--web`, `--strict`
- Full RC4–RC7 pipeline wired in fixture mode: normalizer → ranker → claim extractor → gap analyzer → synthesizer
- Deterministic fixture providers (in-memory, fixed clock at 2024-06-01T00:00:00Z)
- Stdout/stderr discipline: output on stdout, errors on stderr, no tracebacks
- `python -m research_core.cli` entrypoint
- 8 CLI test modules, pytest marker `cli`
- Apache License 2.0
- `examples/external_consumer/` — standalone library usage demo
- `docs/cli/` — CLI, EXIT_CODES, EXTERNAL_CONSUMER references

**RC7 deliverables** (still present):

- `src/research_core/engine.py` — `ResearchEngine` with full RC4–RC7 pipeline
- `src/research_core/synthesis/` — `SynthesisResult`, `DeterministicSynthesizer`
- `src/research_core/renderers/` — `MarkdownRenderer` with snapshot tests
- `src/research_core/contracts/result.py` — `ResearchResult`, `ResearchStatus`

**RC6 deliverables** (still present):

- `src/research_core/analysis/` — `DeterministicGapAnalyzer`, 17 gap conditions
- `docs/diagnostics/GAP_ANALYSIS.md`, `QUALITY_DIAGNOSTICS.md`, `DIAGNOSTIC_CONTRACTS.md`

**RC5 deliverables** (still present):

- `src/research_core/claims/` — `DeterministicClaimExtractor`
- `docs/claims/CLAIM_EXTRACTION.md`, `CLAIM_CONTRACTS.md`

**RC4 deliverables** (still present):

- `src/research_core/normalization/` — `NormalizationService`, `RankingService`

**RC3 deliverables** (still present):

- `src/research_core/adapters/web/` — `WebSearchAdapter`

**RC2 deliverables** (still present):

- `src/research_core/adapters/knowledge/` — `KnowledgeAdapter`

**RC1 deliverables** (still present):

- `src/research_core/contracts/` — all typed domain contracts
- `src/research_core/protocols/` — provider protocol boundaries
- `src/research_core/exceptions.py` — typed exception hierarchy

**RC0 deliverables** (still present):

- `docs/product/PRODUCT_BRIEF.md`
- `docs/architecture/ARCHITECTURE.md`, `DEPENDENCY_RULES.md`, `ROADMAP.md`

---

## Installation

```bash
pip install research-core
```

For development:

```zsh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

Requires Python 3.11 or later.

---

## Development

```zsh
# Run all tests
python3 -m pytest

# CLI tests only
python3 -m pytest -m cli

# Lint
python3 -m ruff check .

# Type check
python3 -m mypy src

# Build wheel
python3 -m build
```

---

## Documentation

| Document | Purpose |
|---|---|
| [CLI Reference](docs/cli/CLI.md) | Commands, options, output formats |
| [Exit Codes](docs/cli/EXIT_CODES.md) | All exit codes with descriptions |
| [External Consumer](docs/cli/EXTERNAL_CONSUMER.md) | Using research-core as a library |
| [Product Brief](docs/product/PRODUCT_BRIEF.md) | Users, use cases, non-goals, risks |
| [Architecture](docs/architecture/ARCHITECTURE.md) | Pipeline, components, boundaries |
| [Contracts Reference](docs/architecture/CONTRACTS.md) | Contract types, validation, serialization |
| [Dependency Rules](docs/architecture/DEPENDENCY_RULES.md) | Enforceable import constraints |
| [Roadmap](docs/architecture/ROADMAP.md) | RC0–RC9 phases and acceptance criteria |
| [Knowledge Adapter](docs/adapters/KNOWLEDGE_ADAPTER.md) | Adapter design, mappings, usage |
| [Web Search Adapter](docs/adapters/WEB_SEARCH_ADAPTER.md) | Web adapter design, extractors, caching |
| [Claim Extraction](docs/claims/CLAIM_EXTRACTION.md) | Pipeline, algorithms, configuration, guarantees |
| [Claim Contracts](docs/claims/CLAIM_CONTRACTS.md) | All RC5 data types with field-by-field reference |
| [Gap Analysis](docs/diagnostics/GAP_ANALYSIS.md) | RC6 gap conditions, severities, configuration |
| [Quality Diagnostics](docs/diagnostics/QUALITY_DIAGNOSTICS.md) | RC6 dimension scoring, overall status rules |
| [Diagnostic Contracts](docs/diagnostics/DIAGNOSTIC_CONTRACTS.md) | All RC6 data types with field-by-field reference |

---

## Non-Goals

`research-core` does not and will not:

- Generate strategy, recommendations, or decisions
- Produce domain-specific report sections
- Depend on editorial, delivery, or CMS layers
- Make LLM calls or HTTP requests in its core pipeline
- Import vendor SDKs (`openai`, `anthropic`, etc.)
- Use third-party CLI libraries (`click`, `typer`, `rich`, `fire`)
- Silently substitute a default profile when the requested profile is absent

---

## Roadmap Summary

| Phase | Description |
|---|---|
| RC0 | Product and Architecture Foundation ✓ |
| RC1 | Core Contracts and Package Boundary ✓ |
| RC2 | Knowledge Adapter ✓ |
| RC3 | Web Search Adapter ✓ |
| RC4 | Evidence Normalization and Ranking ✓ |
| RC5 | Claim Extraction ✓ |
| RC6 | Research Gap Analysis and Quality Diagnostics ✓ |
| RC7 | Synthesis and Renderers ✓ |
| RC8 | Standalone CLI and External Consumer Demo ← current |
| RC9 | Legacy Component Migration |

---

## License

Apache License 2.0. See [LICENSE](LICENSE) for the full text.
