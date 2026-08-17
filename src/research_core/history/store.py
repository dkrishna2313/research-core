"""SQLite-backed query history store for research-core."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from research_core.contracts.result import ResearchResult


_SCHEMA = """
CREATE TABLE IF NOT EXISTS queries (
    query_id        TEXT PRIMARY KEY,
    asked_at        TEXT NOT NULL,
    question        TEXT NOT NULL,
    profiles        TEXT NOT NULL DEFAULT '[]',
    status          TEXT NOT NULL,
    parent_query_id TEXT REFERENCES queries(query_id) ON DELETE SET NULL,
    sources_count   INTEGER NOT NULL DEFAULT 0,
    evidence_count  INTEGER NOT NULL DEFAULT 0,
    claims_count    INTEGER NOT NULL DEFAULT 0,
    result_json     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_queries_asked_at ON queries(asked_at DESC);
"""


@dataclass(frozen=True)
class QueryRecord:
    query_id: str
    asked_at: datetime
    question: str
    profiles: tuple[str, ...]
    status: str
    parent_query_id: str | None
    sources_count: int
    evidence_count: int
    claims_count: int
    result_json: str

    @property
    def short_id(self) -> str:
        return self.query_id[:8]


class HistoryStore:
    """Persists ResearchResult objects to a local SQLite database.

    The database file is created (along with any parent directories) on first
    use. All writes use WAL mode for safe concurrent reads.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        result: ResearchResult,
        *,
        parent_query_id: str | None = None,
    ) -> str:
        """Persist *result* and return the new query_id."""
        from research_core.contracts.serialization import serialize

        query_id = str(uuid.uuid4())
        asked_at = result.completed_at.isoformat()
        profiles_json = json.dumps(list(result.request.profiles))
        result_json = json.dumps(serialize(result), ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO queries
                    (query_id, asked_at, question, profiles, status,
                     parent_query_id, sources_count, evidence_count,
                     claims_count, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    asked_at,
                    result.request.question,
                    profiles_json,
                    result.status.value,
                    parent_query_id,
                    len(result.sources),
                    len(result.evidence),
                    len(result.claims),
                    result_json,
                ),
            )
        return query_id

    def list_queries(
        self,
        *,
        limit: int = 20,
        profile: str | None = None,
    ) -> list[QueryRecord]:
        """Return recent queries, newest first. Optionally filter by profile."""
        with self._connect() as conn:
            if profile is not None:
                rows = conn.execute(
                    """
                    SELECT * FROM queries
                    WHERE profiles LIKE ?
                    ORDER BY asked_at DESC LIMIT ?
                    """,
                    (f'%"{profile}"%', limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM queries ORDER BY asked_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [_row_to_record(r) for r in rows]

    def delete(self, query_id_prefix: str) -> tuple[bool, str]:
        """Delete by full ID or unique short prefix.

        Returns (True, full_id) on success, (False, reason) on failure.
        """
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT query_id FROM queries WHERE query_id LIKE ?",
                (f"{query_id_prefix}%",),
            ).fetchall()
            if not rows:
                return False, f"no history entry matching {query_id_prefix!r}"
            if len(rows) > 1:
                return False, (
                    f"{len(rows)} entries match {query_id_prefix!r} — "
                    "provide more characters to identify a unique entry"
                )
            full_id = rows[0]["query_id"]
            conn.execute("DELETE FROM queries WHERE query_id = ?", (full_id,))
        return True, full_id

    def get(self, query_id_prefix: str) -> QueryRecord | None:
        """Return the record matching a full ID or unique short prefix, or None."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM queries WHERE query_id LIKE ?",
                (f"{query_id_prefix}%",),
            ).fetchall()
        if len(rows) != 1:
            return None
        return _row_to_record(rows[0])

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


def _row_to_record(row: sqlite3.Row) -> QueryRecord:
    return QueryRecord(
        query_id=row["query_id"],
        asked_at=datetime.fromisoformat(row["asked_at"]),
        question=row["question"],
        profiles=tuple(json.loads(row["profiles"])),
        status=row["status"],
        parent_query_id=row["parent_query_id"],
        sources_count=row["sources_count"],
        evidence_count=row["evidence_count"],
        claims_count=row["claims_count"],
        result_json=row["result_json"],
    )


def format_history_table(records: list[QueryRecord]) -> str:
    """Render *records* as a fixed-width text table."""
    header = (
        f"{'ID':<10}  {'Asked at':<16}  {'Profile':<14}  "
        f"{'Status':<8}  {'Src':>3}  {'Ev':>4}  {'Cl':>4}  Question"
    )
    sep = "─" * 94
    lines = [header, sep]
    for r in records:
        asked = r.asked_at.strftime("%Y-%m-%d %H:%M")
        profile_str = ",".join(r.profiles) if r.profiles else "(none)"
        if len(profile_str) > 14:
            profile_str = profile_str[:13] + "…"
        question = r.question if len(r.question) <= 38 else r.question[:37] + "…"
        lines.append(
            f"{r.short_id:<10}  {asked:<16}  {profile_str:<14}  "
            f"{r.status:<8}  {r.sources_count:>3}  {r.evidence_count:>4}  "
            f"{r.claims_count:>4}  {question}"
        )
    return "\n".join(lines) + "\n"
