# Product Brief — research-core

**Version:** RC0
**Status:** Foundation — engine not yet implemented

---

## Product Name

`research-core`

---

## Product Purpose

`research-core` is a reusable Python library that transforms a research question into a structured, traceable, evidence-grounded result. It is a library first. It is not a report generator, a CLI tool, or a domain-specific analytical suite.

The library provides a composable pipeline: knowledge retrieval, optional web acquisition, source normalization, evidence ranking, claim extraction, contradiction detection, research gap analysis, and synthesis. Each stage produces observable intermediate outputs that the caller can inspect, extend, or override.

The canonical output is a structured `ResearchResult` object. Rendering to Markdown, JSON, or any other format is a separate, optional step.

---

## Problem Statement

The predecessor research implementation — `research_agent` inside the `agent-harness` repository — exhibited a set of compounding defects that undermined the reliability of its outputs:

1. **Silent profile fallback.** When the requested research profile was absent, the system quietly substituted an unrelated infrastructure-oriented profile. The caller received no error and no indication that the wrong profile was active.

2. **Domain contamination in the core.** Report sections specific to data-center infrastructure (Power Implications, Cooling Implications, Rack Architecture Implications) were embedded directly in the core research logic. These sections appeared regardless of the research domain.

3. **Claims and evidence conflated.** Generated prose mixed source evidence with synthesized claims, making it impossible to trace which specific evidence supported a given claim.

4. **Weak contradiction handling.** Conflicting market-size estimates, conflicting growth-rate figures, and conflicting definitions were absorbed into narrative summaries rather than surfaced as explicit contradictions.

5. **Misleading gap reporting.** The system reported "no research gaps identified" in runs where no source documents had been loaded, evidence coverage was incomplete, and the evidence base was explicitly flagged as weak.

6. **Web evidence treated as confirmed fact.** Results from commercial and low-authority web sources were incorporated without authority assessment, corroboration checks, or uncertainty qualification.

7. **Orchestration entangled with downstream concerns.** Research orchestration was coupled to strategy generation, editorial generation, recommendation layers, and decision models. Separating research from these layers required rearchitecting the entire pipeline.

`research-core` is designed to prevent each of these defects by construction.

---

## Target Users

### Primary

| User | Description |
|---|---|
| Python application developer | Embeds `research-core` in a larger Python application; calls the library programmatically; does not use a CLI |
| Internal research-platform developer | Builds and maintains the `research-core` library itself; extends provider adapters, analysis services, and renderers |
| Analytical workflow developer | Constructs multi-step analytical pipelines where research is one stage among several; needs structured intermediate outputs and traceability |

### Secondary

| User | Description |
|---|---|
| CLI user | Runs research from the terminal using the standalone CLI introduced in RC8; does not write Python |
| Team embedding research into a larger application | A product team that calls `research-core` as a service dependency and routes its structured outputs into a downstream application layer |

---

## Primary Use Cases

1. **Programmatic research query.** A caller provides a `ResearchRequest` (question, optional profiles, optional web flag) and receives a `ResearchResult` with structured claims, evidence, contradictions, gaps, and quality diagnostics.

2. **Knowledge-store retrieval with provenance.** The caller retrieves evidence from a local knowledge store through the `KnowledgeProvider` interface. The result preserves source identity, retrieval score, and document lineage.

3. **Web-augmented research.** The caller requests web acquisition alongside knowledge retrieval. Web evidence is normalized into the same evidence model as knowledge evidence, but its provenance (`source_type: web`) is preserved separately throughout.

4. **Contradiction surfacing.** The caller receives an explicit list of detected contradictions among claims, including the conflicting values, the sources involved, and the contradiction type (numeric, temporal, definitional, etc.).

5. **Research gap reporting.** The caller receives an evidence-aware gap report. Gaps are produced whenever evidence is missing, weak, incomplete, or stale — not only when the system judges synthesis impossible.

---

## Secondary Use Cases

1. **Profile-filtered research.** The caller passes one or more profiles that supply domain vocabulary, retrieval configuration, or analytical lenses. The profiles are applied transparently; their absence is reported explicitly rather than silently defaulted.

2. **Partial-result inspection.** A caller that needs to inspect intermediate state (retrieved evidence before synthesis, claims before contradiction detection) accesses intermediate structured outputs from the `ResearchTrace`.

3. **Custom renderer integration.** A caller registers a custom renderer to transform the structured `ResearchResult` into a domain-specific format (HTML, a proprietary JSON schema, a slide deck payload) without modifying core logic.

4. **Quality-gated pipeline.** A caller inspects `quality_diagnostics` before deciding whether to use the result downstream, re-run with different parameters, or flag the result for human review.

5. **Consumer application embedding.** A sports analytics platform, a procurement intelligence tool, or a climate policy application embeds `research-core` as its research backbone. The consumer supplies domain profiles and schemas; `research-core` supplies the evidence engine.

---

## Representative User Journeys

### Journey 1 — Application developer, first integration

A developer adds `research-core` as a dependency. They instantiate a `ResearchEngine` with a local knowledge store path. They issue a `ResearchRequest` with a question and receive a `ResearchResult`. They inspect `result.claims` to build a downstream recommendation. No Markdown rendering is involved.

### Journey 2 — Analyst, web-augmented research

An analyst uses the RC8 CLI to run a research query against both a knowledge store and DuckDuckGo web results. They receive a structured result. They observe that two market-size estimates conflict and that three claims are flagged as uncorroborated. They decide whether to trust the output based on `quality_diagnostics.coverage_score` and the explicit contradiction list.

### Journey 3 — Platform developer, custom profile

A platform developer supplies a `sports` profile that defines retrieval weights, a domain vocabulary list, and preferred source types. They issue a `ResearchRequest` with `profiles=["sports"]`. The engine applies the profile. If the profile is not found, the engine raises `UnknownProfileError` rather than silently using a fallback.

### Journey 4 — Pipeline developer, intermediate inspection

A pipeline developer needs to inspect the evidence pool before synthesis to decide whether to augment it with a third data source. They access `result.trace.evidence_pool` (or the equivalent intermediate output defined in RC1). They make the augmentation decision and re-run synthesis.

---

## Inputs

| Input | Type | Notes |
|---|---|---|
| `question` | string | The research question. Required. Non-empty. |
| `profiles` | list of strings | Optional caller-supplied research profiles. Absent means no profile. Unknown profile raises an error or is explicitly handled. |
| `use_web` | bool | Whether to include web acquisition. Default false. |
| `max_web_results` | int | Maximum web results to acquire. Meaningful only when `use_web` is true. |
| `knowledge_store` | path or provider | Path or pre-configured `KnowledgeProvider`. |
| `web_provider` | string or provider | Web provider identifier or pre-configured `WebSearchProvider`. |

Field names and exact signatures are to be defined in RC1.

---

## Outputs

The canonical output is `ResearchResult`. All renderer output is derived from this structure.

| Field | Description |
|---|---|
| `summary` | Synthesized textual summary. Derivable from claims and evidence. |
| `claims` | List of distinct factual or analytical claims extracted from evidence. |
| `evidence` | List of `EvidenceItem` objects, each tied to a source and a retrieval context. |
| `contradictions` | Explicit contradiction groups: conflicting claims, conflict type, sources involved. |
| `research_gaps` | Gaps in coverage, corroboration, recency, or source quality. Never empty when evidence is absent or weak. |
| `open_questions` | Questions the evidence does not resolve. |
| `sources` | Source registry: each source's identity, type, provenance, and quality metadata. |
| `quality_diagnostics` | Multidimensional quality assessment (see Quality Model section below). |
| `trace` | Execution trace: what was retrieved, what was ranked, what was extracted, what decisions were made at each stage. |

Field names may be refined in RC1. The conceptual roles above are stable.

---

## Public API Direction

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

The `ResearchEngine` is not yet implemented. The above is the intended direction.

---

## Structured Result Direction

The `ResearchResult` is the single source of truth. All downstream consumers — renderers, CLI formatters, application layers — derive their outputs from this structure. No component may bypass the structured result to directly consume intermediate state without going through the defined output contract.

Claims must be distinguishable from evidence. A claim is an assertion; evidence is a retrievable artifact that supports, weakens, or contradicts a claim. The two must not be collapsed.

---

## Quality Model Direction

Research quality is multidimensional. It must not be reduced to a single unexplained scalar. The following dimensions are candidates for the `quality_diagnostics` structure (to be finalized in RC6):

| Dimension | Definition |
|---|---|
| Relevance | How closely the retrieved evidence addresses the question |
| Authority | How credible and authoritative the sources are |
| Recency | Whether the evidence reflects current information |
| Corroboration | Whether key claims are supported by multiple independent sources |
| Independence | Whether sources are independent of each other |
| Coverage | Whether important aspects of the question have been addressed |
| Extraction confidence | The confidence level of the claim-extraction process |
| Contradiction severity | The degree to which unresolved contradictions undermine the result |
| Uncertainty | Explicit uncertainty in claims or evidence |
| Completeness | Whether the evidence set is sufficient to support a synthesis |
| Provenance completeness | Whether source identity, type, and lineage are fully traceable |
| Reproducibility | Whether re-running the same request against the same sources would produce the same result |

A composite score may be provided as a convenience, but all component diagnostics must remain visible and individually accessible.

---

## Quality Principles

1. **No silent fallback.** Every absent, unknown, or misconfigured input is surfaced explicitly. The system never substitutes unrelated defaults.

2. **Evidence before claims.** Claims are derived from evidence; evidence is never fabricated from claims.

3. **Contradictions are first-class.** A result that contains unresolved contradictions must expose them explicitly. It must not hide them inside prose.

4. **Gaps are evidence-aware.** A gap report is produced whenever evidence is absent, weak, incomplete, or stale — not only when synthesis fails.

5. **Web evidence is not automatically fact.** Evidence from web sources requires authority, corroboration, and recency assessment before being treated as reliable.

6. **Provenance is never lost.** Every evidence item preserves its source type, origin, retrieval score, and lineage throughout the entire pipeline.

7. **Partial results are explicit.** A result that is incomplete or degraded must be labelled as such and must expose the reasons.

---

## Explicit Non-Goals

`research-core` is not and will not become:

- A strategy engine
- A recommendation engine
- A decision model
- An editorial or report-generation system
- A deliverable generator
- A sports-specific, data-center-specific, or SMR-specific analytical tool
- A replacement for the `research_agent` CLI as currently designed
- A system that embeds domain taxonomies or domain report sections in its core schema
- A system that performs silent profile fallback

---

## Success Criteria

RC0 is successful when:

1. The four required foundation documents exist and are complete.
2. The package installs without errors under Python 3.11.
3. Foundation tests pass: the package imports cleanly, documentation files exist, and prohibited imports are absent.
4. Linting (ruff) and type checking (mypy) pass for the current source package.
5. No domain-specific schema or implementation is present in the package core.
6. No implementation of the research engine exists in the source package.

Later phases will add additional success criteria as each layer is implemented.

---

## Product Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Knowledge Layer coupling | High | Always access through a provider boundary; never import `knowledge.*` directly from core domain contracts |
| Domain contamination creep | High | Enforce no domain-specific content in `src/research_core/` through import boundary tests |
| Silent fallback recurrence | High | Profile handling is fail-loud by design; no default profile registry |
| Quality model oversimplification | Medium | Quality dimensions are individually tracked; composite score is optional and additive |
| Legacy package becoming the default | Medium | `research_agent` components are never imported by default; selective migration occurs only in RC9 |
| LLM dependency inflation | Medium | LLM SDKs are not runtime dependencies; analysis services define clean protocols before implementations are introduced |
| Scope creep into strategy/recommendations | Low | Dependency rules are documented and enforced in tests from RC1 onward |

---

## Assumptions

1. The Knowledge Layer (`knowledge.store`, `knowledge.retriever`) is stable and accessible as a development dependency from RC2 onward.
2. DuckDuckGo via `ddgs` remains the primary web search provider for the initial RC3 adapter.
3. Python 3.11 is acceptable as the minimum version for all target deployment contexts.
4. The library is consumed programmatically (Python import) in all primary use cases; CLI is a secondary delivery mechanism introduced in RC8.
5. Claim extraction and contradiction detection will involve LLM-assisted analysis in later phases, but the core contracts must support deterministic fallback implementations for testing.
6. Consumer applications supply domain schemas, profiles, and taxonomies; `research-core` does not.

---

## Open Product Questions

The following questions remain open and require product-owner input before the indicated phase.

1. **Contradiction threshold:** What severity of contradiction should promote a result from "has unresolved contradictions" to "synthesis not recommended"? (Decision needed before RC5.)

2. **Package distribution:** Will `research-core` be published to PyPI, distributed as a private package, or consumed only as a local editable install within the monorepo context?

---

## Resolved Product Decisions

The following were open questions that have been decided and are now binding on subsequent phases.

### Profile resolution (resolved — binding for RC1)

`ResearchRequest.profiles` accepts profile identifiers as strings. Profile resolution occurs through an explicitly supplied `ProfileProvider` or registry interface; `research-core` does not contain a built-in domain-profile registry. An unknown profile identifier must fail clearly. Silent fallback is prohibited without exception.

### Partial result semantics (resolved — binding for RC6)

- Conditions that prevent creation of any meaningful result (invalid request, unsupported configuration, total provider failure before evidence is produced) raise typed exceptions.
- Conditions that occur after useful evidence, claims, contradictions, gaps, or diagnostics have been produced return `ResearchResult(status="partial")`. The partial result preserves all available structured artifacts.
- A future strict-execution option on the engine may instruct it to raise instead of returning a partial result.
- An empty evidence set is never presented as a successful complete result.

### Synthesis model (resolved — binding for RC7)

Synthesis is provider-based. The core is not coupled to any LLM SDK. An LLM-assisted synthesis provider may be the primary production path. Deterministic synthesis must remain supported for tests, constrained workflows, reproducibility, and fallback behavior. No synthesis implementation is introduced before RC7.

### License

License: To be determined. Decision required before RC8.

---

## Phase Boundaries

| Phase | Product Boundary |
|---|---|
| RC0 | Product and architecture documentation only. No engine. |
| RC1 | Typed contracts and protocols exist. No real retrieval or LLM calls. |
| RC2 | Knowledge retrieval works end-to-end through the provider boundary. |
| RC3 | Web acquisition works end-to-end through the provider boundary. |
| RC4 | Evidence from both sources is normalized and ranked. |
| RC5 | Claims are extracted; contradictions are detected and represented. |
| RC6 | Research gaps and quality diagnostics are first-class outputs. |
| RC7 | Synthesis produces a complete `ResearchResult`; Markdown renderer is available. |
| RC8 | Standalone CLI is functional; external consumer demo exists. |
| RC9 | Selected legacy components migrated; migration complete. |
