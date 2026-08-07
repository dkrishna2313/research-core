"""
Stable exit-code contract for the research-core CLI.

Exit codes are part of the public API and must not change between patch releases.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Documented exit codes returned by main().

    SUCCESS             = 0   Valid result (COMPLETE or PARTIAL) written to stdout.
    USAGE_ERROR         = 2   Invalid CLI arguments or missing required subcommand.
    INVALID_REQUEST     = 3   Research question or profile ID was invalid.
    UNKNOWN_PROFILE     = 4   A specified profile ID could not be resolved.
    PROVIDER_FAILURE    = 5   All providers failed or returned no evidence.
    EXECUTION_FAILURE   = 6   Pipeline execution failure (incomplete research, etc.).
    OUTPUT_FAILURE      = 7   Rendering or serialization of the result failed.
    CONFIGURATION_FAILURE = 8 CLI is not configured (no providers; use --fixture).
    """

    SUCCESS = 0
    USAGE_ERROR = 2
    INVALID_REQUEST = 3
    UNKNOWN_PROFILE = 4
    PROVIDER_FAILURE = 5
    EXECUTION_FAILURE = 6
    OUTPUT_FAILURE = 7
    CONFIGURATION_FAILURE = 8
