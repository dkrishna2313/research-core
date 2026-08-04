"""
Example: query the knowledge-layer via KnowledgeAdapter.

Usage:
    python examples/knowledge_adapter_query.py [query] [--store PATH] [--top-k N]

Requires:
    pip install research-core[knowledge]
    A populated knowledge_store directory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_DEFAULT_STORE = Path(__file__).parent.parent / "knowledge_store"


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the knowledge layer via research-core")
    parser.add_argument("query", nargs="?", default="SMR deployment barriers", help="Retrieval query")
    parser.add_argument("--store", type=Path, default=_DEFAULT_STORE, help="Path to knowledge_store")
    parser.add_argument("--top-k", type=int, default=10, help="Maximum results to return")
    parser.add_argument("--profile", type=str, default=None, help="Optional profile filter")
    args = parser.parse_args()

    from research_core.adapters.knowledge import KnowledgeAdapter

    if not KnowledgeAdapter.is_available():
        print("ERROR: knowledge package (dc-power-agent) is not installed.")
        print("  pip install research-core[knowledge]")
        sys.exit(1)

    if not args.store.exists():
        print(f"ERROR: knowledge_store not found at {args.store}")
        print("  Set --store to a valid knowledge_store directory.")
        sys.exit(1)

    from research_core.contracts.request import ResearchRequest
    from research_core.protocols.knowledge import KnowledgeRetrievalRequest

    request = ResearchRequest(
        question=args.query,
        max_knowledge_results=args.top_k,
    )
    profiles: tuple[str, ...] = (args.profile,) if args.profile else ()
    k_request = KnowledgeRetrievalRequest(
        query=args.query,
        parent_request=request,
        profiles=profiles,
    )

    adapter = KnowledgeAdapter(store_root=args.store, load_sources=True)
    result = adapter.retrieve(k_request)

    print(f"\nQuery:    {args.query!r}")
    print(f"Store:    {args.store}")
    print(f"Profile:  {args.profile or '(all)'}")
    print(f"Evidence: {len(result.evidence)} items")
    print(f"Sources:  {len(result.sources)} records")

    if not result.evidence:
        print("\n(no results)")
        return

    print()
    for i, ev in enumerate(result.evidence, start=1):
        score = ev.provenance.retrieval_score
        score_str = f"{score:.3f}" if score is not None else "n/a"
        rank = ev.provenance.retrieval_rank or i
        statement = ev.content
        if len(statement) > 100:
            statement = statement[:99] + "…"
        print(f"  {rank:>3}  score={score_str}  {statement}")

    if result.sources:
        print("\nSources:")
        for src in result.sources:
            line = f"  [{src.source_id[:12]}]  {src.title}"
            if src.publisher:
                line += f"  ({src.publisher})"
            print(line)


if __name__ == "__main__":
    main()
