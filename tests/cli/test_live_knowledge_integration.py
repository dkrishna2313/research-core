"""Integration smoke tests — live KnowledgeAdapter against the real knowledge_store.

These tests require the knowledge store at _KNOWLEDGE_STORE to exist and the
knowledge package (dc-power-agent) to be installed. The whole module is skipped
if the path is absent.

NOTE: The store currently has 0 indexed evidence items — sources are present
but embeddings have not been generated.  Queries return empty evidence, which
causes the engine to raise ProviderExecutionError → exit code 5 (PROVIDER_FAILURE).
These tests treat exit code 5 as an acceptable result for an un-indexed store.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode

_KNOWLEDGE_STORE = Path(
    "/Users/dkrishna/Documents/Clients/Climate/ARI/AI-Apps/knowledge-layer/knowledge_store"
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.knowledge,
    pytest.mark.skipif(
        not _KNOWLEDGE_STORE.exists(),
        reason=f"real knowledge store not present at {_KNOWLEDGE_STORE}",
    ),
]


class TestLiveKnowledgeSmokeTest:
    def test_live_query_reaches_provider_layer(self, capsys):
        """Engine must build and reach the provider layer (never exit 8)."""
        code = main(
            [
                "run",
                "What is the ROI of sports sponsorship?",
                "--knowledge-store",
                str(_KNOWLEDGE_STORE),
            ]
        )
        captured = capsys.readouterr()
        assert code != ExitCode.CONFIGURATION_FAILURE, (
            f"engine never built (exit 8); stderr: {captured.err}"
        )

    def test_live_query_exits_0_or_5(self, capsys):
        """Empty-evidence store → PROVIDER_FAILURE(5) or SUCCESS(0) with partial result."""
        code = main(
            [
                "run",
                "Women's sports marketing trends 2025",
                "--knowledge-store",
                str(_KNOWLEDGE_STORE),
            ]
        )
        assert code in (ExitCode.SUCCESS, ExitCode.PROVIDER_FAILURE), (
            f"expected 0 or 5; got {code}\nstderr: {capsys.readouterr().err}"
        )

    def test_live_query_with_profile_does_not_crash(self, capsys):
        """Pass-through provider must not raise for arbitrary profile IDs."""
        code = main(
            [
                "run",
                "What is the value of women's sports?",
                "--knowledge-store",
                str(_KNOWLEDGE_STORE),
                "--profile",
                "marketing",
            ]
        )
        assert code != ExitCode.CONFIGURATION_FAILURE

    def test_provider_failure_produces_no_stdout(self, capsys):
        """PROVIDER_FAILURE must not leak partial content to stdout."""
        code = main(
            [
                "run",
                "test question",
                "--knowledge-store",
                str(_KNOWLEDGE_STORE),
            ]
        )
        captured = capsys.readouterr()
        if code == ExitCode.PROVIDER_FAILURE:
            assert captured.out == ""

    def test_json_format_with_live_store(self, capsys):
        """JSON format flag must not trigger a configuration error."""
        code = main(
            [
                "run",
                "Sports sponsorship value",
                "--knowledge-store",
                str(_KNOWLEDGE_STORE),
                "--format",
                "json",
            ]
        )
        assert code != ExitCode.CONFIGURATION_FAILURE
