"""
Profile resolution protocol.

ProfileProvider resolves caller-supplied profile identifiers into structured
configuration objects. Profiles may constrain retrieval scope, quality
thresholds, synthesis style, or any other dimension the provider chooses.

There is no built-in domain registry. All profile semantics are defined by
the ProfileProvider implementation. Unrecognized profile IDs must cause
UnknownProfileError to be raised.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from research_core.contracts.common import EMPTY_METADATA, Metadata, ProfileId


@dataclass(frozen=True)
class ResolvedProfile:
    """A profile identifier resolved to its configuration.

    profile_id: the identifier supplied by the caller.
    config: arbitrary configuration data understood by the implementation.
            The framework does not inspect or validate config contents.
    display_name: optional human-readable label for the profile.
    description: optional description for diagnostics or rendering.
    """

    profile_id: ProfileId
    config: dict[str, Any] = field(default_factory=dict)
    display_name: str = ""
    description: str = ""
    metadata: Metadata = field(default_factory=lambda: EMPTY_METADATA)


@runtime_checkable
class ProfileProvider(Protocol):
    """Structural protocol for resolving profile identifiers.

    resolve() is called with a single profile_id and must return a
    ResolvedProfile.  If the profile_id is not recognized, implementations
    must raise UnknownProfileError (from research_core.exceptions).

    resolve_many() is a convenience method that calls resolve() for each ID.
    Default protocol implementors may override it for batched resolution.
    """

    def resolve(self, profile_id: ProfileId) -> ResolvedProfile:
        """Resolve a single profile identifier to its configuration.

        Raises:
            UnknownProfileError: if profile_id is not known.
        """
        ...

    def resolve_many(
        self, profile_ids: tuple[ProfileId, ...]
    ) -> tuple[ResolvedProfile, ...]:
        """Resolve multiple profile identifiers in order.

        Default implementation calls resolve() for each ID sequentially.
        Raises:
            UnknownProfileError: if any profile_id is not known.
        """
        return tuple(self.resolve(pid) for pid in profile_ids)
