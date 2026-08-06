# Using research-core as a Library

`research-core` is designed for use both as a CLI tool and as an importable Python library. This document covers the library usage path.

## Installation

```bash
pip install research-core
```

## Minimum viable consumer

```python
from research_core.cli.providers import build_fixture_engine
from research_core.contracts.request import ResearchRequest
from research_core.renderers import MarkdownRenderer

engine = build_fixture_engine()
request = ResearchRequest(question="What are the key climate tipping points?")
result = engine.run(request)

print(MarkdownRenderer().render(result))
```

## Key entry points

### Engine

`build_fixture_engine(*, use_web=False, clock=None)` — builds a fully wired `ResearchEngine` with deterministic in-memory providers. Suitable for development, testing, and demos.

```python
from research_core.cli.providers import build_fixture_engine

engine = build_fixture_engine()
```

### Request

`ResearchRequest` — the input contract for a research run.

```python
from research_core.contracts.request import ResearchRequest

request = ResearchRequest(
    question="Your research question",
    profiles=["default"],
    use_web=False,
    strict=False,
)
```

### Result

`ResearchResult` — the output contract. Key fields:

| Field | Type | Description |
|-------|------|-------------|
| `status` | `ResearchStatus` | `COMPLETE` or `PARTIAL` |
| `sources` | `list[Source]` | Raw sources gathered |
| `evidence` | `list[EvidenceItem]` | Processed evidence |
| `ranked_evidence` | `list[RankedEvidence]` | Evidence after ranking |
| `claims` | `list[Claim]` | Extracted claims |
| `gap_analysis` | `GapAnalysis \| None` | Identified research gaps |
| `synthesis` | `SynthesisResult \| None` | Final synthesis with narrative |
| `trace` | `ResearchTrace` | Timing and pipeline diagnostics |

### Rendering

```python
from research_core.renderers import MarkdownRenderer

md = MarkdownRenderer().render(result)
```

### Serialization

```python
from research_core.contracts.serialization import serialize
import json

payload = serialize(result)
print(json.dumps(payload, indent=2, sort_keys=True))
```

## Full example

See `examples/external_consumer/consumer.py` for a runnable demo.

## Architecture constraints

- `research-core` makes no LLM calls and has no network dependencies in its core pipeline.
- No vendor SDKs are imported (`openai`, `anthropic`, etc.).
- The CLI uses only the Python standard library for argument parsing (`argparse`).
- All providers implement protocols — you can supply your own implementations.
