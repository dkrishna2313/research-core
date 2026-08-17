"""
KnowledgeAdapter — KnowledgeProvider implementation backed by the knowledge-layer.

The knowledge package (dc-power-agent) is imported lazily on the first
retrieve() call. This allows the module to be imported and the adapter class
to be instantiated without the backend installed. A ProviderUnavailableError
is raised at retrieve() time if the package is absent.

Multi-profile retrieval:
    The knowledge-layer EvidenceRetriever.retrieve() accepts a single profile
    string. When request.profiles contains multiple entries, the adapter issues
    one retrieval call per profile and merges results by deduplicating on
    evidence_id (highest score wins), then re-sorts by score and re-ranks.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from research_core.contracts.sources import Source
from research_core.exceptions import ProviderExecutionError, ProviderUnavailableError, UnknownProfileError
from research_core.protocols.knowledge import KnowledgeRetrievalRequest, KnowledgeRetrievalResult

from .mapping import map_evidence_item, map_source

if TYPE_CHECKING:
    from knowledge.retriever import EvidenceRetriever, RetrievedEvidence
    from knowledge.store import KnowledgeStore


class KnowledgeAdapter:
    """KnowledgeProvider backed by a knowledge-layer KnowledgeStore.

    Parameters
    ----------
    store_root:
        Path to the knowledge_store directory (passed to KnowledgeStore).
    load_sources:
        When True (default), Source records are loaded during retrieval and
        included in KnowledgeRetrievalResult.sources. Set to False to reduce
        latency when source metadata is not needed.
    """

    def __init__(
        self,
        store_root: str | Path,
        *,
        load_sources: bool = True,
    ) -> None:
        self._store_root = Path(store_root)
        self._load_sources = load_sources
        self._retriever: EvidenceRetriever | None = None
        self._store: KnowledgeStore | None = None

    @staticmethod
    def is_available() -> bool:
        """Return True if the knowledge package (dc-power-agent) is importable."""
        try:
            import knowledge  # noqa: F401

            return True
        except ImportError:
            return False

    def retrieve(self, request: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        """Retrieve evidence and sources matching the knowledge retrieval request.

        Multi-profile requests result in per-profile retrieval calls with
        deduplication by evidence_id (highest score wins).

        Raises
        ------
        ProviderUnavailableError
            If the knowledge package is not installed or the store cannot be opened.
        ProviderExecutionError
            If retrieval fails for an unexpected reason after the store is open.
        """
        retriever = self._ensure_retriever()
        retrieved_at = datetime.now(UTC)
        top_k = request.effective_max_results

        try:
            raw_items = self._fetch_items(retriever, request, top_k)
        except (ProviderUnavailableError, ProviderExecutionError, UnknownProfileError):
            raise
        except Exception as exc:
            raise ProviderExecutionError(
                f"knowledge retrieval failed for query {request.query!r}: {exc}"
            ) from exc

        sources: list[Source] = []
        seen_source_ids: set[str] = set()
        evidence_list = []

        for item in raw_items:
            ev_item = map_evidence_item(item, request.query, retrieved_at)
            if ev_item is None:
                continue
            evidence_list.append(ev_item)

            if self._load_sources and item.source is not None:
                src = map_source(item.source)
                if src.source_id not in seen_source_ids:
                    sources.append(src)
                    seen_source_ids.add(src.source_id)

        return KnowledgeRetrievalResult(
            sources=tuple(sources),
            evidence=tuple(evidence_list),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_retriever(self) -> EvidenceRetriever:
        if self._retriever is None:
            try:
                from knowledge.retriever import EvidenceRetriever
                from knowledge.store import KnowledgeStore
            except ImportError as exc:
                raise ProviderUnavailableError(
                    f"knowledge package (dc-power-agent) is not installed: {exc}"
                ) from exc

            try:
                store = KnowledgeStore(root=self._store_root)
                self._store = store
                self._retriever = EvidenceRetriever(store=store)
            except Exception as exc:
                raise ProviderUnavailableError(
                    f"failed to initialize KnowledgeStore at {self._store_root!r}: {exc}"
                ) from exc

        return self._retriever

    def _fetch_items(
        self,
        retriever: EvidenceRetriever,
        request: KnowledgeRetrievalRequest,
        top_k: int,
    ) -> list[RetrievedEvidence]:
        profiles = request.profiles

        if not profiles:
            result = retriever.retrieve(
                request.query,
                top_k=top_k,
                load_sources=self._load_sources,
            )
            return result.items  # type: ignore[no-any-return]

        for profile in profiles:
            self._assert_profile_exists(profile)

        if len(profiles) == 1:
            result = retriever.retrieve(
                request.query,
                profile=profiles[0],
                top_k=top_k,
                load_sources=self._load_sources,
            )
            return result.items  # type: ignore[no-any-return]

        return self._merge_multi_profile(retriever, request, profiles, top_k)

    def _merge_multi_profile(
        self,
        retriever: EvidenceRetriever,
        request: KnowledgeRetrievalRequest,
        profiles: tuple[str, ...],
        top_k: int,
    ) -> list[RetrievedEvidence]:
        """Retrieve per profile, dedup by evidence_id (highest score wins), re-rank."""
        best: dict[str, RetrievedEvidence] = {}

        for profile in profiles:
            result = retriever.retrieve(
                request.query,
                profile=profile,
                top_k=top_k,
                load_sources=self._load_sources,
            )
            for item in result.items:
                eid = item.evidence.evidence_id
                if eid not in best or item.score > best[eid].score:
                    best[eid] = item

        merged = sorted(best.values(), key=lambda x: x.score, reverse=True)[:top_k]

        for new_rank, item in enumerate(merged, start=1):
            item.rank = new_rank

        return merged

    def _assert_profile_exists(self, profile_id: str) -> None:
        """Raise UnknownProfileError if no evidence in the store is tagged with profile_id."""
        store = self._store
        if store is None:
            return
        for domain in store.available_domains():
            for ev in store.iter_evidence(domain):
                if profile_id in ev.profile_ids:
                    return
        raise UnknownProfileError(
            profile_id,
            f"unknown profile {profile_id!r} — not found in knowledge store. "
            f"Run 'python3 -m knowledge list-profiles' to see available profiles.",
        )
