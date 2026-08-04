"""
Example: search the web via WebSearchAdapter.

Usage:
    python examples/web_search_query.py [query] [--max-results N] [--max-pages N]
    python examples/web_search_query.py [query] [--max-results N] [--cache-dir PATH]

Requires:
    pip install research-core[web]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the web via research-core")
    parser.add_argument(
        "query",
        nargs="?",
        default="small modular reactor deployment barriers",
        help="Search query",
    )
    parser.add_argument("--max-results", type=int, default=10, help="Max search results")
    parser.add_argument("--max-pages", type=int, default=5, help="Max pages to fetch")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Optional disk cache directory",
    )
    args = parser.parse_args()

    from research_core.adapters.web import WebSearchAdapter

    if not WebSearchAdapter.is_available():
        print("ERROR: ddgs (or duckduckgo_search) is not installed.")
        print("  pip install research-core[web]")
        sys.exit(1)

    cache = None
    if args.cache_dir is not None:
        from research_core.adapters.web.cache import WebCache

        cache = WebCache(args.cache_dir)
        print(f"Cache:    {args.cache_dir}")

    from research_core.contracts.request import ResearchRequest
    from research_core.protocols.web import WebSearchRequest

    parent = ResearchRequest(
        question=args.query,
        max_web_results=args.max_results,
        max_web_pages=args.max_pages,
    )
    request = WebSearchRequest(query=args.query, parent_request=parent)

    adapter = WebSearchAdapter(cache=cache)
    result = adapter.search(request)

    print(f"\nQuery:    {args.query!r}")
    print(f"Sources:  {len(result.sources)}")
    print(f"Evidence: {len(result.evidence)}")

    if not result.evidence:
        print("\n(no results)")
        return

    print()
    for ev in result.evidence:
        rank = ev.provenance.retrieval_rank or 0
        snippet = ev.content
        if len(snippet) > 100:
            snippet = snippet[:99] + "…"
        print(f"  {rank:>3}  {snippet}")

    if result.sources:
        print("\nSources:")
        for src in result.sources:
            title = src.title or src.url or "(no title)"
            print(f"  [{src.source_id[:12]}]  {title}")
            if src.url:
                print(f"           {src.url}")


if __name__ == "__main__":
    main()
