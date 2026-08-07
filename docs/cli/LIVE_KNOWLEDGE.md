# Live Knowledge CLI Execution

RC8.1 adds the ability to run `research-core` against a real Knowledge Layer store.
Instead of the deterministic in-memory `--fixture` providers, the CLI wires the
`KnowledgeAdapter` directly to a local `knowledge_store` directory.

## Requirements

- The `dc-power-agent` (knowledge package) must be installed:

  ```bash
  pip install research-core[knowledge]
  ```

- A populated `knowledge_store` directory on the local filesystem.

## Basic usage

```bash
research-core run "QUESTION" --knowledge-store /path/to/knowledge_store
```

Examples:

```bash
research-core run "What is the ROI of women's sports sponsorship?" \
    --knowledge-store ~/projects/knowledge-layer/knowledge_store

# JSON output
research-core run "Sports marketing trends 2025" \
    --knowledge-store ~/projects/knowledge-layer/knowledge_store \
    --format json

# With a domain profile
research-core run "Brand value in women's sports" \
    --knowledge-store ~/projects/knowledge-layer/knowledge_store \
    --profile marketing
```

## Environment variable

Instead of passing `--knowledge-store` on every invocation, set:

```bash
export RESEARCH_CORE_KNOWLEDGE_STORE=/path/to/knowledge_store
research-core run "Your research question"
```

The `--knowledge-store` CLI flag takes priority over the environment variable when both are present.

## Profile support

The `--profile` flag passes a profile identifier to the `KnowledgeAdapter`. The adapter
uses this to filter evidence to the named domain at retrieval time. Any string is accepted —
there is no server-side profile registry in live mode.

```bash
research-core run "Question" \
    --knowledge-store /path/to/store \
    --profile marketing
```

## Constraints

| Constraint | Reason |
|-----------|--------|
| `--fixture` and `--knowledge-store` are mutually exclusive | Both define how evidence is sourced; only one can be active |
| `--web` is not supported in live knowledge mode | Web retrieval uses a separate adapter not yet wired to live mode |

Attempting either combination exits with code `8` (`CONFIGURATION_FAILURE`) and a
descriptive error message on stderr.

## Empty stores

If the knowledge store has not had evidence extracted and indexed, retrieval returns
zero items. The engine treats empty evidence as a provider failure, and the CLI exits
with code `5` (`PROVIDER_FAILURE`).

To populate a store, use the knowledge-layer indexing tools to extract evidence from
source documents and generate embeddings before running queries.

## Exit codes in live mode

| Code | Scenario |
|------|----------|
| `0` | Research completed (COMPLETE or PARTIAL result) |
| `5` | Knowledge adapter failed or returned zero evidence |
| `6` | Engine execution failed (strict mode or pipeline error) |
| `8` | `--fixture` + `--knowledge-store` conflict, `--web` in live mode, invalid/missing path |

See [EXIT_CODES.md](EXIT_CODES.md) for the full reference.
