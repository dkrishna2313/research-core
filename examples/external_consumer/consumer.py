"""External consumer demo — shows how to use research-core as a library."""

from __future__ import annotations

import json

from research_core.cli.providers import build_fixture_engine
from research_core.contracts.request import ResearchRequest
from research_core.contracts.result import ResearchStatus
from research_core.renderers import MarkdownRenderer


def run_demo() -> None:
    engine = build_fixture_engine()

    request = ResearchRequest(
        question="What are the key drivers of Arctic sea ice decline?",
        profiles=["default"],
        use_web=False,
        strict=False,
    )

    result = engine.run(request)

    print(f"Status  : {result.status.value}")
    print(f"Sources : {len(result.sources)}")
    print(f"Evidence: {len(result.evidence)}")
    print(f"Claims  : {len(result.claims)}")
    if result.synthesis:
        print(f"Narrative: {result.synthesis.narrative[:80]}...")
    print()

    if result.status in (ResearchStatus.COMPLETE, ResearchStatus.PARTIAL):
        md = MarkdownRenderer().render(result)
        print(md)
    else:
        print("Research did not complete successfully.")


def run_json_demo() -> None:
    from research_core.contracts.serialization import serialize

    engine = build_fixture_engine()
    request = ResearchRequest(question="Arctic permafrost carbon feedback")
    result = engine.run(request)

    payload = serialize(result)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    import sys

    if "--json" in sys.argv:
        run_json_demo()
    else:
        run_demo()
