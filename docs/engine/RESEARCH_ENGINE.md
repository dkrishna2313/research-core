# ResearchEngine — RC7

`ResearchEngine` coordinates the research pipeline from a `ResearchRequest` to
a `ResearchResult`. All stage implementations are injected; the engine contains
no domain logic and imports no vendor SDK.

## Stage order

| Stage | TraceStage | Skipped if |
|---|---|---|
| 1 | INIT | — |
| 2 | PROFILE_RESOLUTION | `request.profiles` is empty |
| 3 | RETRIEVAL (knowledge) | no `knowledge_provider` |
| 3 | RETRIEVAL (web) | `request.use_web=False` or no `web_search_provider` |
| 4 | EXTRACTION | no `claim_extractor` |
| 5 | CONTRADICTION_DETECTION | no `contradiction_detector` |
| 6 | GAP_ANALYSIS | no `gap_analyzer` |
| 7 | SYNTHESIS | no `synthesizer` |
| 8 | FINALIZATION | — |

## Partial-result semantics

- **Empty evidence** (no evidence from any provider): raises `ProviderExecutionError`.
  No result object is produced.
- **Stage failure** (extraction, contradiction detection, gap analysis, synthesis):
  the stage is recorded as FAILED in the trace; the engine continues with
  `status=PARTIAL`. All artifacts produced before the failure are preserved.
- **Synthesis failure**: `synthesis=None` in the result; all earlier artifacts intact.
- **`request.strict=True`**: if the result would be PARTIAL, raises
  `IncompleteResearchError` before returning.

## Construction

```python
from research_core.engine import ResearchEngine
from research_core.synthesis import DeterministicSynthesizer

engine = ResearchEngine(
    knowledge_provider=my_knowledge_provider,
    claim_extractor=my_claim_extractor,
    gap_analyzer=my_gap_analyzer,
    synthesizer=DeterministicSynthesizer(),
    # clock=my_clock,  # inject for deterministic test timestamps
)
result = engine.run(request)
```

All constructor parameters are keyword-only and optional. The engine gracefully
skips any stage whose provider is `None`.

## Clock injection

The `clock` parameter accepts a `Callable[[], datetime]`. It defaults to
`datetime.now(UTC)`. Override it in tests to produce deterministic trace
timestamps:

```python
from datetime import UTC, datetime

FIXED_TS = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)
engine = ResearchEngine(..., clock=lambda: FIXED_TS)
```

## Quality computation

After retrieval, the engine computes `QualityDiagnostics` from the mean of
per-evidence-item quality signals (relevance, authority, recency,
extraction_confidence). Dimensions with no values stay `None`.

## Import boundary

`engine.py` must not import from `research_core.adapters` or any optional
vendor SDK (openai, anthropic, ddgs, trafilatura, etc.). The import boundary
test at `tests/engine/test_import_boundaries.py` enforces this via static AST
analysis.

## Exceptions

| Exception | When |
|---|---|
| `UnknownProfileError` | Profile ID in request cannot be resolved |
| `ProviderExecutionError` | No evidence retrieved from any provider |
| `IncompleteResearchError` | `strict=True` and result is PARTIAL |
