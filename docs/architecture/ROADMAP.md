# Roadmap — research-core

**Version:** RC6

---

## Sequencing Rules

The following rules govern phase ordering and are non-negotiable:

1. RC0 contains no production engine implementation.
2. RC1 creates typed contracts and protocols but performs no real retrieval and makes no LLM calls.
3. Knowledge and web integrations occur only through provider interfaces defined in RC1.
4. Structured results (`ResearchResult`) are defined before any rendering is introduced.
5. Quality diagnostics and research gaps are first-class outputs, not afterthoughts.
6. Legacy migration (`research_agent` components) is selective and occurs only after the clean architecture exists in RC7.
7. The legacy package must not become the new architecture by default. No legacy component is imported until it has passed a clean-architecture review.

---

## RC0 — Product and Architecture Foundation ✓ COMPLETE

### Objective

Establish the product definition, architecture documentation, dependency rules, and development tooling. No engine implementation.

### Scope

- `docs/product/PRODUCT_BRIEF.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/architecture/DEPENDENCY_RULES.md`
- `docs/architecture/ROADMAP.md`
- `README.md`
- `pyproject.toml` with `src` layout, Python 3.11 minimum, dev tooling
- `.gitignore`
- `src/research_core/__init__.py` (package docstring and version only)
- Foundation tests: package imports cleanly, docs exist, prohibited imports absent

### Non-Scope

- Any production implementation: retrieval, web search, LLM calls, evidence ranking, claim extraction, contradiction detection, gap analysis, synthesis, renderers, CLI
- Protocol definitions
- Domain model class definitions
- Provider adapters

### Dependencies

None. This is the first phase.

### Deliverables

1. Four foundation documents
2. Valid `pyproject.toml` that installs under Python 3.11
3. Minimal `src/research_core/__init__.py`
4. Foundation test suite

### Acceptance Criteria

- All four foundation documents exist and are complete
- Package installs: `pip install -e ".[dev]"` succeeds
- `python3 -m pytest` passes
- `python3 -m ruff check .` passes
- `python3 -m mypy src` passes
- No prohibited imports present in `src/` or `tests/`
- No domain-specific schema in package core
- Documentation does not claim the research engine is operational

### Exit Criteria

All acceptance criteria are met and the final commit exists on `feature/rc0-product-architecture-foundation`. Working tree is clean.

---

## RC1 — Core Contracts and Package Boundary ✓ COMPLETE

### Objective

Define the typed, domain-neutral data contracts and provider protocols that all later phases build on. No real retrieval or LLM calls.

### Scope

- `ResearchRequest` — typed dataclass or Protocol
- `ResearchResult` — typed dataclass with all field stubs
- `Claim`, `EvidenceItem`, `Source`, `Provenance` — typed dataclasses
- `Contradiction` — typed dataclass with ConflictType enum
- `ResearchGap` — typed dataclass with GapType enum
- `OpenQuestion` — typed dataclass
- `QualityDiagnostics` — typed dataclass
- `ResearchTrace` — typed dataclass
- Provider protocols: `KnowledgeProvider`, `WebSearchProvider`, `ProfileProvider`, `Synthesizer`
- Analysis protocols: `ClaimExtractor`, `ContradictionDetector`, `GapAnalyzer`
- Renderer protocol: `Renderer`
- `UnknownProfileError` and other exception types
- `ResearchResult.status` field (`"complete"` | `"partial"`)
- Import boundary tests for all prohibited patterns
- Contract tests verifying invariants

### Non-Scope

- Any working adapter implementation
- Any LLM call
- Actual evidence retrieval
- Synthesis

### Dependencies

RC0 complete.

### Deliverables

1. All typed contracts in `src/research_core/contracts/`
2. All protocols in `src/research_core/protocols/`
3. Exception types in `src/research_core/exceptions.py`
4. Import boundary tests
5. Contract invariant tests

### Acceptance Criteria

- All contract types are importable with no side effects
- All protocol interfaces are importable
- `mypy --strict` passes on all contract and protocol modules
- Import boundary tests pass
- No external package imports in `src/research_core/contracts/`
- `UnknownProfileError` is raised when an unknown profile is passed (no fallback)

### Exit Criteria

All acceptance criteria met on `feature/rc1-contracts`. No real retrieval, adapter, or LLM code introduced.

---

## RC2 — Knowledge Adapter ✓ COMPLETE

### Objective

Implement the production `KnowledgeProvider` adapter connecting `research-core` to the knowledge-layer (`dc-power-agent`). Knowledge retrieval works end-to-end through the provider boundary.

### Scope

- `KnowledgeRetrievalResult` dataclass (RC1 contract correction — returns sources + evidence)
- `KnowledgeAdapter` in `src/research_core/adapters/knowledge/` implementing `KnowledgeProvider`
- Score normalization from knowledge-layer's `[0, ~2.1]` range to `[0.0, 1.0]`
- Multi-profile retrieval with per-profile calls, dedup by evidence_id, re-rank
- Lazy `knowledge` package import — adapter importable without backend installed
- `research-core[knowledge]` optional dependency in `pyproject.toml`
- Six test files covering mapping, adapter behaviour, profiles, exceptions, optional dependency, integration
- `docs/adapters/KNOWLEDGE_ADAPTER.md`
- `examples/knowledge_adapter_query.py`

### Non-Scope

- Web acquisition
- Analysis services
- Synthesis

### Dependencies

RC1 complete. `knowledge-layer` package (`dc-power-agent`) available at the configured path.

### Deliverables

1. `src/research_core/adapters/knowledge/adapter.py` — `KnowledgeAdapter`
2. `src/research_core/adapters/knowledge/mapping.py` — type mapping and score normalization
3. `tests/adapters/knowledge/` — six test modules, 95 tests
4. `docs/adapters/KNOWLEDGE_ADAPTER.md`
5. `examples/knowledge_adapter_query.py`
6. `pyproject.toml` optional dependency `research-core[knowledge]`

### Acceptance Criteria

- `KnowledgeAdapter` satisfies the `KnowledgeProvider` protocol (`isinstance` check passes)
- Retrieved `EvidenceItem` objects have `source_type = "knowledge"` and full provenance
- All retrieval scores normalized to `[0.0, 1.0]`
- `KnowledgeAdapter` is importable without `knowledge` installed
- Core contracts not modified except `KnowledgeRetrievalResult` addition (corrects RC1 defect)
- Import boundary tests still pass; `knowledge.*` not imported at `research_core` module level
- 301 tests passing, mypy strict clean, ruff clean

### Exit Criteria

All acceptance criteria met. `KnowledgeAdapter` is importable and functional against the knowledge_store.

---

## RC3 — Web Search Adapter ✓ COMPLETE

### Objective

Wrap the DuckDuckGo web-search and page-acquisition implementation behind the `WebSearchProvider` protocol.

### Scope

- `WebSearchAdapter` implementing `WebSearchProvider` backed by DuckDuckGo
- `WebSearchResult` dataclass (RC3 contract correction — returns sources + evidence)
- Web page acquisition via `requests`, content extraction via `trafilatura` / `pypdf` / `python-docx`
- `ddgs`, `requests`, `trafilatura`, `pypdf`, `python-docx` as optional adapter dependencies
- Optional disk cache (`WebCache`) with atomic writes
- Full test suite: unit tests require no network; integration tests gated by `RUN_NETWORK_TESTS=1`
- Protocol conformance tests

### Non-Scope

- The legacy `research_agent.cli` — not imported
- Web evidence quality scoring — quality scoring is RC4's responsibility

### Dependencies

RC1 complete. RC2 optional (independent).

### Deliverables

1. `src/research_core/adapters/web/` — adapter, cache, extractors, fetch, mapping, search, models
2. `tests/adapters/web/` — ten test modules (481 passing, 9 network-gated)
3. `docs/adapters/WEB_SEARCH_ADAPTER.md`
4. `examples/web_search_query.py`
5. `pyproject.toml` optional dependency `research-core[web]`

### Acceptance Criteria

- `WebSearchAdapter` satisfies the `WebSearchProvider` protocol (`isinstance` check passes) ✓
- Web `EvidenceItem` objects have `source_type = "web"` and URL provenance ✓
- No live network calls in the default test suite (unit tests use injected stubs) ✓
- `research_agent.cli` is not imported anywhere ✓
- Import boundary tests still pass ✓
- 481 tests passing, mypy strict clean, ruff clean ✓

### Exit Criteria

All acceptance criteria met. `WebSearchAdapter` is importable and functional.

---

## RC4 — Evidence Normalization and Ranking ✓ COMPLETE

### Objective

Normalize evidence from both knowledge and web sources into a unified, ranked evidence pool. Preserve provenance and apply quality scoring.

### Scope

- Source normalization service: unifies `EvidenceItem` schema across source types
- Evidence ranking service: scores by relevance, authority, recency
- Quality scoring per evidence item (initial formula)
- Knowledge and web provenance preserved and distinct after normalization
- Deterministic ranking algorithm with no LLM dependency
- Tests with fixed evidence fixtures

### Non-Scope

- Claim extraction
- Contradiction detection
- LLM-based reranking (may be added as an optional path later)

### Dependencies

RC2 and RC3 complete (or stub implementations available).

### Deliverables

1. `src/research_core/analysis/normalizer.py`
2. `src/research_core/analysis/ranker.py`
3. Quality scoring function or class
4. Tests with deterministic fixtures

### Acceptance Criteria

- Knowledge and web evidence items share a unified schema after normalization
- `source_type` field is preserved and never altered
- Ranking is deterministic for the same input
- Empty evidence pool produces a `ResearchGap` for missing evidence
- Import boundary tests still pass

### Exit Criteria

All acceptance criteria met. Normalizer and ranker are independently testable.

---

## RC5 — Claim Extraction ✓ COMPLETE

### Objective

Extract discrete claims from the ranked evidence pool. Deterministic, provider-neutral, no LLM calls.

### Scope

- `research_core.claims` package: contracts, config, extractor, candidate segmentation, classification, deduplication
- `DeterministicClaimExtractor` — rule-based, no LLM, no network
- Sentence segmentation, clause splitting, assertiveness filter
- Claim type, modality, polarity, quantitative/temporal/attribution extraction
- Exact deduplication (same-parent overlap, same evidence, cross-source preserved)
- Full diagnostics with count reconciliation
- 18 test modules in `tests/claims/`, pytest marker `claims`
- `docs/claims/CLAIM_EXTRACTION.md` and `docs/claims/CLAIM_CONTRACTS.md`
- `examples/extract_claims.py`

### Non-Scope

- Contradiction detection (deferred to RC6)
- Gap analysis
- Synthesis
- LLM-assisted extraction

### Dependencies

RC4 complete.

### Deliverables

1. `src/research_core/claims/` — full package
2. `tests/claims/` — 17 test modules
3. `docs/claims/CLAIM_EXTRACTION.md`
4. `docs/claims/CLAIM_CONTRACTS.md`
5. `examples/extract_claims.py`

### Acceptance Criteria

- Claims are distinct from evidence items (no conflation) ✓
- Each claim references its supporting evidence IDs ✓
- Extraction is deterministic for identical input ✓
- No LLM, network, or NLP library imports in claims package ✓
- Import boundary tests pass ✓
- `mypy --strict` clean, ruff clean ✓

### Exit Criteria

All acceptance criteria met. `DeterministicClaimExtractor` is independently testable with deterministic fixtures.

---

## RC6 — Research Gap Analysis and Quality Diagnostics ✓ COMPLETE

### Objective

Make research gaps and quality diagnostics first-class outputs. The system never reports "no gaps" when evidence is absent, weak, or incomplete.

### Scope

- `research_core.analysis` package: contracts, config, aggregate, quality, conditions, analyzer
- `research_core.diagnostics` thin re-export for clean public API path
- `GapAnalyzer` protocol + `DeterministicGapAnalyzer` — 17 deterministic conditions
- `QualityDiagnosticsResult` — five quality dimensions, aggregated per-dimension and overall
- `GapAnalysisConfig` — all thresholds configurable with stable fingerprint
- 17 test modules in `tests/diagnostics/`, pytest marker `diagnostics`
- `docs/diagnostics/` — GAP_ANALYSIS.md, QUALITY_DIAGNOSTICS.md, DIAGNOSTIC_CONTRACTS.md
- `examples/analyze_gaps.py`
- Partial result semantics: any gap → PARTIAL; only gap-free with evidence → COMPLETE

### Non-Scope

- Contradiction detection
- Synthesis
- Rendering

### Dependencies

RC5 complete.

### Deliverables

1. `src/research_core/analysis/` — full package (contracts, config, aggregate, quality, conditions, analyzer)
2. `src/research_core/diagnostics/__init__.py` — thin re-export
3. `tests/diagnostics/` — 17 test modules, 199 tests
4. `docs/diagnostics/GAP_ANALYSIS.md`
5. `docs/diagnostics/QUALITY_DIAGNOSTICS.md`
6. `docs/diagnostics/DIAGNOSTIC_CONTRACTS.md`
7. `examples/analyze_gaps.py`

### Acceptance Criteria

- All nine architecture gap conditions plus eight additional conditions evaluated ✓
- `QualityDiagnosticsResult` exposes all five dimension scores individually ✓
- An empty evidence pool always produces CRITICAL gaps and PARTIAL status ✓
- Gap IDs are deterministic and stable across runs with same inputs ✓
- Import boundary tests still pass ✓
- `mypy --strict` clean, ruff clean ✓

### Exit Criteria

All acceptance criteria met. `DeterministicGapAnalyzer` is independently testable with deterministic fixtures.

---

## RC7 — Synthesis and Renderers

### Objective

Produce a complete, structured `ResearchResult`. Introduce Markdown as the first renderer.

### Scope

- `Synthesizer` provider protocol (already defined in RC1) — first concrete implementation (deterministic baseline)
- `ResearchEngine` — full pipeline orchestration from request to result
- `MarkdownRenderer` — derives Markdown from `ResearchResult`
- `ResearchResult` with all fields populated from a real pipeline run
- Integration test with a fixed evidence fixture
- Renderer snapshot tests

### Non-Scope

- LLM-assisted synthesis (optional path for later)
- CLI (RC8)
- Domain-specific renderers

### Dependencies

RC6 complete.

### Deliverables

1. `src/research_core/synthesis/synthesizer.py`
2. `src/research_core/engine.py`
3. `src/research_core/renderers/markdown.py`
4. Integration test
5. Renderer snapshot test

### Acceptance Criteria

- `ResearchEngine.run()` produces a `ResearchResult` from a fixture request
- `ResearchResult` contains non-empty `claims`, `evidence`, `sources`, `quality_diagnostics`, `trace`
- `MarkdownRenderer` produces valid Markdown from any `ResearchResult`
- The Markdown renderer does not modify or produce the `ResearchResult`
- Synthesis failure produces a partial result, not an exception (unless the request was invalid)
- Import boundary tests still pass

### Exit Criteria

All acceptance criteria met. Full pipeline is testable end-to-end.

---

## RC8 — Standalone CLI and External Consumer Demo

### Objective

Provide a usable standalone CLI and an external consumer demo that shows how to embed `research-core` in an application.

### Scope

- `src/research_core/cli.py` (or `src/research_core/__main__.py`)
- Entry point registered in `pyproject.toml`
- CLI arguments: question, optional profile, optional web flag, output format
- Unknown profile raises an error and exits with a non-zero code
- CLI tests
- `examples/` consumer demo script

### Non-Scope

- Domain-specific CLI flags
- Strategy or recommendation output
- Legacy CLI replacement

### Dependencies

RC7 complete.

### Deliverables

1. `src/research_core/cli.py`
2. Entry point in `pyproject.toml`
3. CLI tests
4. `examples/demo_consumer.py`

### Acceptance Criteria

- `research-core run "question"` executes and produces a structured result or Markdown output
- Unknown profile exits non-zero with a clear error message
- CLI does not import domain-specific logic
- Consumer demo runs against a local fixture without a live knowledge store
- Import boundary tests still pass

### Exit Criteria

All acceptance criteria met. CLI is independently installable and functional.

---

## RC9 — Legacy Component Migration

### Objective

Selectively migrate proven, stable components from `research_agent` into `research-core`. Discard components that do not meet the clean-architecture standard.

### Scope

- Audit `research_agent/web_search.py` and `research_agent/web_cache.py` for migration suitability
- Migrate only components that pass a clean-architecture review
- Add or update tests for any migrated component
- Remove any migrated component's dependency on `research_agent.cli` or other prohibited modules

### Non-Scope

- Copying the complete `research_agent` package
- Importing `research_agent.cli` into any `research-core` module
- Changing the public API of `research-core` to match `research_agent`'s API

### Dependencies

RC8 complete. Clean architecture fully in place.

### Deliverables

1. Migration audit report (markdown)
2. Migrated components (if any) with tests
3. Documentation of what was migrated and what was not

### Acceptance Criteria

- No migrated component imports from `research_agent.cli`
- Every migrated component has test coverage
- Import boundary tests still pass after migration
- The public API of `research-core` is not broken by migration

### Exit Criteria

All acceptance criteria met. Migration audit report exists. Working tree is clean.

---

## Open Questions

1. **Contradiction threshold** — What severity of contradiction promotes a result to "synthesis not recommended"? Decision needed before RC5.
2. **Package distribution channel** — PyPI, private registry, or local editable install only.
3. **LLM provider selection** — Which LLM SDK(s) are introduced in RC5/RC7 optional paths.

---

## Resolved Decisions

The following were open questions that have been decided.

### Profile resolution

`ResearchRequest.profiles` accepts string identifiers. Resolution occurs through an explicitly supplied `ProfileProvider` or registry interface; no built-in domain registry exists in `research-core`. Unknown identifiers raise `UnknownProfileError`. Silent fallback is prohibited. — **Binding for RC1.**

### Partial result semantics

- Failures that prevent any meaningful result raise typed exceptions.
- Failures after useful evidence is produced return `ResearchResult(status="partial")` with all available artifacts preserved.
- A future strict-execution option may raise instead of returning a partial result.
- Empty evidence is never a successful complete result. — **Binding for RC6.**

### Synthesis model

Synthesis is provider-based via a `Synthesizer` protocol. The core is not coupled to any LLM SDK. LLM-assisted synthesis may be the primary production provider. Deterministic synthesis must remain supported for tests, reproducibility, and fallback. — **Binding for RC7.**

### License

License: To be determined. Decision required before RC8.
