# Dependency Rules — research-core

**Version:** RC3
**Status:** Normative — these rules are enforced from RC1 onward through import boundary tests

---

## Dependency Direction

The permitted dependency direction is:

```
knowledge-layer  (external)
        ↓
research-core
        ↓
consumer application
```

The arrow means "may depend on." No arrow may be reversed. `research-core` must never import from a consumer application. A consumer application must never be a dependency of `research-core`.

---

## Layer Dependency Map

```
Layer                         May depend on
─────────────────────────────────────────────────────────────────────
core domain contracts         Python standard library only
                              approved internal utilities (no external packages)

provider protocols            core domain contracts

provider adapters             provider protocols
                              core domain contracts
                              narrow external packages (per adapter)

analysis services             core domain contracts
                              own analysis protocols

orchestration                 core domain contracts
                              provider protocols
                              analysis services

synthesis                     core domain contracts

renderers                     core domain contracts (result structures only)
                              NOT analysis services
                              NOT provider adapters

CLI                           public application API (ResearchEngine, ResearchRequest)
                              NOT core contracts directly
                              NOT provider adapters directly

consumer applications         research-core public API
                              NOT internal research-core modules
```

---

## Permitted Dependency Examples

The following flows are explicitly permitted:

```
research_core.adapters.knowledge.adapter
    → research_core.protocols.knowledge            (OK — adapter implements its own protocol)
    → research_core.contracts.evidence             (OK — uses core EvidenceItem)
    → knowledge.store                              (OK — narrow external dependency, in adapter only)
    → knowledge.retriever                          (OK — narrow external dependency, in adapter only; lazy import)

research_core.adapters.web.adapter
    → research_core.protocols.web                  (OK — adapter implements its own protocol)
    → research_core.contracts.evidence             (OK — uses core EvidenceItem)
    → ddgs                                         (OK — narrow external dependency, in adapter only; lazy import)
    → requests                                     (OK — narrow external dependency, in adapter only; lazy import)
    → trafilatura                                  (OK — narrow external dependency, in adapter only; lazy import)
    → pypdf                                        (OK — narrow external dependency, in adapter only; lazy import)
    → docx                                         (OK — narrow external dependency, in adapter only; lazy import)

research_core.analysis.contradiction_detector
    → research_core.contracts.claim                (OK — uses core Claim)
    → research_core.contracts.contradiction        (OK — uses core Contradiction)

research_core.renderers.markdown
    → research_core.contracts.result               (OK — consumes ResearchResult)

research_core.engine
    → research_core.protocols.knowledge_provider   (OK — orchestrator uses protocol, not adapter)
    → research_core.analysis.claim_extractor       (OK — orchestrator coordinates analysis)
    → research_core.contracts.request              (OK — validates ResearchRequest)
```

---

## Prohibited Dependency Examples

The following flows are explicitly prohibited:

```
research_core.contracts.*
    → knowledge.*                                  PROHIBITED — core contracts must not import external packages
    → functional_agents.*                          PROHIBITED
    → strategy.*                                   PROHIBITED
    → editorial.*                                  PROHIBITED
    → deliverables.*                               PROHIBITED
    → recommendations.*                            PROHIBITED
    → decision_models.*                            PROHIBITED
    → research_agent.cli                           PROHIBITED

research_core.renderers.*
    → research_core.analysis.*                     PROHIBITED — renderers consume results, not analysis services
    → research_core.providers.*                    PROHIBITED — renderers have no provider awareness

research_core.*
    → os.environ  (inside domain model classes)    PROHIBITED — no env reads in domain models
    → open(...)   (inside domain model classes)    PROHIBITED — no filesystem access in domain models
    → requests.*  (inside core contracts)          PROHIBITED — no network access in domain models

consumer_app.*
    → research_core  (allowed as a dependency)
research_core.*
    → consumer_app.*                               PROHIBITED — library must never depend on its consumers
```

---

## Explicitly Prohibited Imports

The following module paths must never appear in `import` or `from ... import` statements within `src/research_core/` or `tests/`:

| Prohibited import | Reason |
|---|---|
| `functional_agents` | Downstream consumer concern |
| `strategy` | Downstream consumer concern |
| `editorial` | Downstream consumer concern |
| `deliverables` | Downstream consumer concern |
| `recommendations` | Downstream consumer concern |
| `decision_models` | Downstream consumer concern |
| `research_agent.cli` | Legacy CLI; must not become a dependency |
| Any domain-specific consumer package | Downstream consumer concern |

Exception: a test that _verifies_ one of these is absent may reference the module name as a string, not as an actual import.

---

## Prohibited Patterns

Beyond specific module names, the following patterns are prohibited anywhere in `src/research_core/`:

### Circular dependencies

No two modules within `research_core` may directly or transitively import each other.

### Provider-specific types in core contracts

A core contract type (e.g., `EvidenceItem`) must not have a field typed as a provider-specific class (e.g., `KnowledgeStoreResult` from the external knowledge package). Core contracts use only primitives, stdlib types, and other core contract types.

### Renderer concerns inside analysis models

An analysis service must not produce HTML, Markdown, or formatted strings as part of its primary output. It produces structured objects. Formatting is the renderer's responsibility.

### CLI concerns inside the library core

Argument parsing, `sys.argv` access, `print()` calls for output, and `sys.exit()` calls must not appear in `src/research_core/` except in the CLI module (introduced in RC8).

### Environment-variable reads inside domain entities

A domain model class (`ResearchRequest`, `ResearchResult`, `Claim`, `EvidenceItem`, etc.) must not call `os.environ`, `os.getenv`, or any configuration-reading function. Configuration is injected by the caller.

### Filesystem access from domain models

Domain model objects must not call `open()`, `pathlib.Path.read_text()`, or equivalent. Data is passed to them; they do not fetch it.

### Network access from domain models

Domain model objects must not call `requests.get()`, `urllib.request.urlopen()`, or equivalent. Network access is the adapter's responsibility.

### Hidden global provider selection

There must be no global singleton that selects a provider based on environment variables or module-level configuration. Provider selection is explicit and caller-controlled.

### Implicit profile fallback

If the caller requests `profiles=["sports"]` and no `sports` profile is found, the system must raise an error or return an explicit "no profile applied" result. It must never silently activate a different profile.

### Domain taxonomies embedded in the package core

Module-level constants, data classes, or configuration dictionaries that encode sports-specific, data-center-specific, SMR-specific, or any other domain vocabulary must not exist in `src/research_core/`. Domain configuration is always caller-supplied.

---

## Enforcement

Import boundary tests in `tests/test_import_boundaries.py` (introduced in RC1) verify:

1. None of the prohibited module names are importable from within `research_core`.
2. The `research_core` package can be imported without triggering any side effects.
3. Core domain contract modules contain no imports of external packages.
4. Provider adapters contain no imports of other provider adapters.
5. Renderers contain no imports of analysis service modules.

Optional static enforcement via `import-linter` or equivalent may be introduced in RC8. Import boundary tests are the primary enforcement mechanism.

---

## Rationale

These rules exist because the predecessor system (`research_agent`) exhibited:

- Orchestration importing strategy, editorial, and recommendation layers
- Core research logic containing data-center-specific domain sections
- A default profile registry that silently substituted unrelated profiles
- Renderers that reached into analysis internals to format intermediate data

Each prohibited pattern maps directly to one of these observed defects. The rules are not stylistic preferences; they are architectural invariants derived from production failures.
