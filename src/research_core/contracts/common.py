"""
Shared type aliases, identifiers, enums, and metadata utilities.

All domain contracts depend on this module. This module depends only on the
Python standard library.
"""

from __future__ import annotations

import types
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Identifier type aliases
# All identifiers are non-empty strings. Type aliases communicate intent
# without introducing wrapper types that would add friction for callers.
# ---------------------------------------------------------------------------

ClaimId = str
EvidenceId = str
SourceId = str
DocumentId = str
ContradictionId = str
ResearchGapId = str
TraceEventId = str
ProfileId = str

# ---------------------------------------------------------------------------
# Metadata type
# A JSON-compatible key-value store used for extensible annotations.
# Stored internally as MappingProxyType to prevent mutation through caller
# references. Accepts any Mapping[str, Any] at construction time.
# ---------------------------------------------------------------------------

Metadata = Mapping[str, Any]

#: Canonical empty metadata instance — reused as a sentinel for no metadata.
EMPTY_METADATA: Metadata = types.MappingProxyType({})


def _to_proxy(data: Metadata | None) -> types.MappingProxyType[str, Any]:
    """Return a MappingProxyType copy of *data*, or EMPTY_METADATA if None."""
    if data is None:
        return types.MappingProxyType({})
    if isinstance(data, types.MappingProxyType):
        return data
    return types.MappingProxyType(dict(data))


# ---------------------------------------------------------------------------
# SourceType
# ---------------------------------------------------------------------------


class SourceType(StrEnum):
    """The origin category of a source or evidence item.

    KNOWLEDGE — retrieved from a local knowledge store.
    WEB       — acquired from a web search provider.

    The enum is extensible: future source types (e.g. DATABASE, API) may be
    added without changing the core contracts.
    """

    KNOWLEDGE = "knowledge"
    WEB = "web"
