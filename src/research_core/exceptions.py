"""
Typed exception hierarchy for research-core.

Failures that prevent construction of a meaningful result raise typed exceptions.
When useful evidence or analysis has been produced, the engine returns a partial
ResearchResult rather than raising. Only conditions where no useful work exists
(or where strict mode is requested) result in an exception.
"""

from __future__ import annotations


class ResearchCoreError(Exception):
    """Base class for all research-core exceptions."""


class ContractValidationError(ResearchCoreError):
    """Raised when a domain contract receives an invalid value.

    This covers field-level validation failures detected at construction time:
    empty required strings, out-of-range scores, inconsistent cross-references,
    and similar structural errors.
    """


class InvalidResearchRequestError(ResearchCoreError):
    """Raised when a ResearchRequest contains invalid or missing fields.

    Examples: empty question, blank profile identifier, negative result limit.
    This exception is always raised before the pipeline begins.
    """


class UnknownProfileError(ResearchCoreError):
    """Raised when a profile identifier cannot be resolved.

    The engine never silently substitutes a default profile. When a
    ProfileProvider cannot resolve a requested profile identifier, it must
    raise this exception rather than returning a fallback.

    Attributes:
        profile_id: The unresolvable profile identifier.
    """

    def __init__(self, profile_id: str, message: str | None = None) -> None:
        self.profile_id = profile_id
        super().__init__(message or f"unknown profile identifier: {profile_id!r}")


class UnsupportedConfigurationError(ResearchCoreError):
    """Raised when the engine is initialized with an unsupported configuration.

    Examples: incompatible option combinations, provider type not supported
    in the current build. Raised at engine initialization time, before
    any request is processed.
    """


class ProviderUnavailableError(ResearchCoreError):
    """Raised when a required provider cannot be reached or initialized.

    If a fallback provider is available, the engine may degrade to a partial
    result instead of raising. This exception is raised only when no fallback
    exists and no useful work is possible.
    """


class ProviderExecutionError(ResearchCoreError):
    """Raised when a provider call fails during execution.

    The engine may raise this or convert it into a partial ResearchResult
    depending on how much work was completed before the failure.
    """


class IncompleteResearchError(ResearchCoreError):
    """Raised when strict mode is requested and the result would be partial.

    When ResearchRequest.strict is True, the engine raises this instead of
    returning ResearchResult(status=ResearchStatus.PARTIAL).
    """
