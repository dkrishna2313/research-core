"""
ResearchRequest — the caller-supplied input to a research operation.

Profiles are string identifiers resolved at runtime through a caller-supplied
ProfileProvider. This contract does not resolve profiles; it validates and
normalizes the request before the engine runs.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field
from datetime import date

from research_core.contracts.common import EMPTY_METADATA, Metadata, ProfileId, _to_proxy
from research_core.exceptions import InvalidResearchRequestError


@dataclass(frozen=True)
class ResearchRequest:
    """Validated, immutable input for a single research operation.

    Profiles are optional caller-supplied identifiers that a ProfileProvider
    will resolve at runtime. An absent profiles tuple means the request is
    explicitly profile-free; this is not equivalent to supplying an unknown
    profile identifier.

    Validation rules (applied in __post_init__):
    - question: non-empty after trimming; leading/trailing whitespace stripped
    - profiles: each identifier non-empty after trimming; duplicates removed
      while preserving first-occurrence order; stored as an immutable tuple
    - max_knowledge_results, max_web_results, max_web_pages: must be positive
    - as_of_date: optional; no future-date restriction at contract level
    - strict: when True, the engine raises IncompleteResearchError instead of
      returning a partial result
    - metadata: defensively copied to MappingProxyType
    """

    question: str
    profiles: tuple[ProfileId, ...] = field(default_factory=tuple)
    use_knowledge: bool = True
    use_web: bool = False
    max_knowledge_results: int = 10
    max_web_results: int = 5
    max_web_pages: int = 5
    language: str = "en"
    as_of_date: date | None = None
    strict: bool = False
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)

    def __post_init__(self) -> None:
        # Normalize and validate question
        stripped_question = self.question.strip()
        if not stripped_question:
            raise InvalidResearchRequestError(
                "question must be non-empty after trimming whitespace"
            )
        object.__setattr__(self, "question", stripped_question)

        # Normalize profiles: trim, reject blanks, deduplicate preserving order
        normalized: list[ProfileId] = []
        seen: set[ProfileId] = set()
        for raw in self.profiles:
            p = raw.strip()
            if not p:
                raise InvalidResearchRequestError(
                    f"profile identifier must not be blank, got {raw!r}"
                )
            if p not in seen:
                seen.add(p)
                normalized.append(p)
        object.__setattr__(self, "profiles", tuple(normalized))

        # Validate result limits
        if self.max_knowledge_results <= 0:
            raise InvalidResearchRequestError(
                f"max_knowledge_results must be positive, got {self.max_knowledge_results}"
            )
        if self.max_web_results <= 0:
            raise InvalidResearchRequestError(
                f"max_web_results must be positive, got {self.max_web_results}"
            )
        if self.max_web_pages <= 0:
            raise InvalidResearchRequestError(
                f"max_web_pages must be positive, got {self.max_web_pages}"
            )

        # Normalize metadata
        if not isinstance(self.metadata, types.MappingProxyType):
            object.__setattr__(self, "metadata", _to_proxy(self.metadata))

    @property
    def has_profiles(self) -> bool:
        """True if at least one profile identifier was specified."""
        return len(self.profiles) > 0
