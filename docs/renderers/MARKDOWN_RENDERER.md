# MarkdownRenderer — RC7

`MarkdownRenderer` converts a `ResearchResult` into a Markdown string.

## Design constraints

- **Pure.** The renderer never mutates the result, runs providers, makes network
  calls, or writes files.
- **Deterministic.** Identical inputs produce identical outputs across calls,
  instances, and Python versions.
- **No external libraries.** No Jinja2, mistune, markdown, or rich. Output is
  assembled with plain string operations.

## Output format

- Ends with exactly one `\n`.
- No trailing whitespace on any line.
- IDs are rendered in backtick code spans.
- User text (questions, claim statements, narratives) is rendered as-is.
- `None` quality scores → `"Unavailable"`.
- `0.0` quality scores → `"0.000"`.

## Sections

1. **Research Result** — title
2. **Status** — value, completeness flag, completed timestamp, partial notice
3. **Research Question**
4. **Executive Summary** — synthesis narrative or "not available"
5. **Sources** — list with title, type, URL, publisher where present
6. **Evidence** — numbered list with relevance/authority scores and content
7. **Claims** — numbered list with type and supporting evidence IDs
8. **Quality Diagnostics** — table of all dimensions
9. **Research Gaps** — numbered list with severity, type, description, action
10. **Synthesis** — narrative, model, key findings
11. **Contradictions** — section only when contradictions exist
12. **Open Questions** — section only when open questions exist
13. **Execution Trace** — stage events
14. **Limitations** — boilerplate disclaimer

## Usage

```python
from research_core.renderers import MarkdownRenderer

renderer = MarkdownRenderer()
md = renderer.render(result)
print(md)

# Write to a file
from pathlib import Path
Path("report.md").write_text(md, encoding="utf-8")
```

## Snapshot tests

Committed snapshots live in `tests/renderers/snapshots/`. To regenerate after
an intentional rendering change:

```bash
REGENERATE_SNAPSHOTS=1 pytest tests/renderers/test_snapshot.py
```

Then review and commit the updated snapshot files.
