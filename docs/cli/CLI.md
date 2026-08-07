# research-core CLI

The `research-core` command is a standalone CLI for running research pipelines.

## Installation

```bash
pip install research-core
```

After installation, the `research-core` command is available on your PATH.

## Quick start

```bash
# Run with deterministic fixture data (no network, no API keys)
research-core run "What are the key drivers of Arctic sea ice decline?" --fixture

# JSON output
research-core run "What is permafrost carbon feedback?" --fixture --format json

# Via Python module
python -m research_core.cli run "Your research question" --fixture
```

## Commands

### `run`

Execute a research pipeline for a given question.

```
research-core run QUESTION [OPTIONS]
```

**Arguments:**

| Name | Description |
|------|-------------|
| `QUESTION` | Research question (required, must not be blank) |

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--format {markdown,json}` | `markdown` | Output format |
| `--fixture` | off | Use deterministic in-memory fixture providers |
| `--profile PROFILE_ID` | `default` | Profile ID to use |
| `--web` | off | Enable web evidence providers |
| `--strict` | off | Fail on any missing evidence |

**Examples:**

```bash
# Markdown output (default)
research-core run "Climate tipping points" --fixture

# JSON output
research-core run "Climate tipping points" --fixture --format json

# Specific profile
research-core run "Ocean acidification" --fixture --profile demo
```

## Output formats

### Markdown (default)

A human-readable document beginning with a `#` heading. Suitable for piping to a file or terminal display.

```bash
research-core run "question" --fixture > report.md
```

### JSON

A machine-readable serialized `ResearchResult`. All keys are sorted alphabetically. Suitable for piping to `jq` or other JSON processors.

```bash
research-core run "question" --fixture --format json | jq '.status'
```

## Fixture mode

`--fixture` wires a fully deterministic, in-memory research pipeline. It requires no network access and no API keys. All providers return fixed data and the clock is pinned to `2024-06-01T00:00:00Z`.

Fixture mode is useful for:
- Local development and testing
- CI pipelines
- Demonstrating the library without external dependencies

## Exit codes

See [EXIT_CODES.md](EXIT_CODES.md) for the full list of exit codes.

## Using as a library

See [EXTERNAL_CONSUMER.md](EXTERNAL_CONSUMER.md) and `examples/external_consumer/`.
