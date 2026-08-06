# External Consumer Demo

Shows how to use `research-core` as a Python library dependency from an external project.

## Setup

```bash
pip install research-core
python consumer.py
```

Or, from this directory with an editable install of research-core:

```bash
pip install -e ../../
python consumer.py
```

## What it demonstrates

- Importing `build_fixture_engine` from `research_core.cli.providers`
- Constructing a `ResearchRequest` directly
- Running the engine to get a `ResearchResult`
- Rendering the result as Markdown using `MarkdownRenderer`
- Serializing the result to JSON using `serialize()`

## JSON output

```bash
python consumer.py --json
```

## Structure

```
my-research-app/
├── pyproject.toml   # declares research-core>=0.8.0 dependency
└── consumer.py      # library usage demo
```
