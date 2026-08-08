"""
CLI-internal provider module — fixture re-export and live knowledge engine builder.

The fixture engine implementation lives in the public package:
    research_core.fixtures

External consumers should import from there::

    from research_core.fixtures import build_fixture_engine

This module re-exports build_fixture_engine so existing CLI internals and
tests that import from research_core.cli.providers continue to work.

build_live_knowledge_engine() constructs a ResearchEngine backed by the
real KnowledgeAdapter pointed at a local knowledge_store directory.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from research_core.engine import ResearchEngine

from research_core.fixtures.engine import (
    FIXTURE_CLOCK_TS,
    FIXTURE_PROFILE_IDS,
    build_fixture_engine,
)
from research_core.protocols.profiles import ResolvedProfile


class _PassThroughProfileProvider:
    """Resolves any profile_id without restriction.

    In live Knowledge mode, profile filtering is handled by KnowledgeAdapter
    at retrieval time. This provider accepts any string and returns a minimal
    ResolvedProfile so the engine can proceed.
    """

    def resolve(self, profile_id: str) -> ResolvedProfile:
        return ResolvedProfile(
            profile_id=profile_id,
            display_name=profile_id,
            description=f"Live knowledge profile: {profile_id}",
        )

    def resolve_many(self, profile_ids: tuple[str, ...]) -> tuple[ResolvedProfile, ...]:
        return tuple(self.resolve(pid) for pid in profile_ids)


def build_live_knowledge_engine(
    knowledge_store_path: Path,
    *,
    clock: Callable[[], datetime] | None = None,
) -> ResearchEngine:
    """Return a ResearchEngine backed by a live KnowledgeAdapter.

    All imports of optional components are deferred to this function body so
    the module can be imported without the knowledge package installed.
    A ProviderUnavailableError is raised at retrieve() time if the package
    is absent.

    Parameters
    ----------
    knowledge_store_path:
        Path to the knowledge_store directory (passed to KnowledgeAdapter).
    clock:
        Optional callable returning the current datetime. Defaults to
        datetime.now(UTC) at runtime.
    """
    from research_core.adapters.knowledge.adapter import KnowledgeAdapter
    from research_core.analysis.analyzer import DeterministicGapAnalyzer
    from research_core.claims.extractor import DeterministicClaimExtractor
    from research_core.engine import ResearchEngine
    from research_core.normalization.normalizer import EvidenceNormalizer
    from research_core.normalization.ranker import EvidenceRanker
    from research_core.synthesis import DeterministicSynthesizer

    return ResearchEngine(
        profile_provider=_PassThroughProfileProvider(),
        knowledge_provider=KnowledgeAdapter(store_root=knowledge_store_path),
        evidence_normalizer=EvidenceNormalizer(),
        evidence_ranker=EvidenceRanker(),
        rc5_claim_extractor=DeterministicClaimExtractor(),
        rc6_gap_analyzer=DeterministicGapAnalyzer(),
        synthesizer=DeterministicSynthesizer(),
        clock=clock,
    )


__all__ = [
    "build_fixture_engine",
    "build_live_knowledge_engine",
    "FIXTURE_CLOCK_TS",
    "FIXTURE_PROFILE_IDS",
]
