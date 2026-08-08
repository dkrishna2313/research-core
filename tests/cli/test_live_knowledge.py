"""Tests for live knowledge mode CLI behavior — conflict detection and path validation."""

from __future__ import annotations

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode


@pytest.mark.cli
@pytest.mark.knowledge
class TestLiveKnowledgeConflicts:
    def test_fixture_and_knowledge_store_are_mutually_exclusive(self, tmp_path, capsys):
        code = main(["run", "test question", "--fixture", "--knowledge-store", str(tmp_path)])
        assert code == ExitCode.CONFIGURATION_FAILURE
        err = capsys.readouterr().err
        assert "mutually exclusive" in err

    def test_web_unsupported_in_live_knowledge_mode(self, tmp_path, capsys):
        code = main(["run", "test question", "--knowledge-store", str(tmp_path), "--web"])
        assert code == ExitCode.CONFIGURATION_FAILURE
        err = capsys.readouterr().err
        assert "--web" in err

    def test_nonexistent_knowledge_store_path_exits_8(self, tmp_path, capsys):
        nonexistent = tmp_path / "does_not_exist"
        code = main(["run", "test question", "--knowledge-store", str(nonexistent)])
        assert code == ExitCode.CONFIGURATION_FAILURE

    def test_fixture_knowledge_store_conflict_message_mentions_both_flags(self, tmp_path, capsys):
        main(["run", "q", "--fixture", "--knowledge-store", str(tmp_path)])
        err = capsys.readouterr().err
        assert "--fixture" in err
        assert "--knowledge-store" in err

    def test_conflict_produces_no_stdout(self, tmp_path, capsys):
        main(["run", "test question", "--fixture", "--knowledge-store", str(tmp_path)])
        assert capsys.readouterr().out == ""

    def test_invalid_path_produces_no_stdout(self, tmp_path, capsys):
        nonexistent = tmp_path / "missing"
        main(["run", "test question", "--knowledge-store", str(nonexistent)])
        assert capsys.readouterr().out == ""

    def test_web_conflict_produces_no_stdout(self, tmp_path, capsys):
        main(["run", "test question", "--knowledge-store", str(tmp_path), "--web"])
        assert capsys.readouterr().out == ""


@pytest.mark.cli
@pytest.mark.knowledge
class TestLiveKnowledgeEnvVar:
    def test_env_var_resolves_knowledge_store(self, tmp_path, monkeypatch, capsys):
        """With env var set, omitting --knowledge-store still selects live mode."""
        monkeypatch.setenv("RESEARCH_CORE_KNOWLEDGE_STORE", str(tmp_path))
        code = main(["run", "test question"])
        # Path is valid but knowledge package may be absent
        # → PROVIDER_FAILURE, not CONFIGURATION_FAILURE
        assert code != ExitCode.CONFIGURATION_FAILURE

    def test_env_var_nonexistent_path_exits_8(self, tmp_path, monkeypatch, capsys):
        nonexistent = tmp_path / "missing"
        monkeypatch.setenv("RESEARCH_CORE_KNOWLEDGE_STORE", str(nonexistent))
        code = main(["run", "test question"])
        assert code == ExitCode.CONFIGURATION_FAILURE

    def test_cli_knowledge_store_flag_overrides_env(self, tmp_path, monkeypatch, capsys):
        env_path = tmp_path / "env_store"
        cli_path = tmp_path / "cli_store"
        cli_path.mkdir()
        monkeypatch.setenv("RESEARCH_CORE_KNOWLEDGE_STORE", str(env_path))
        code = main(["run", "test question", "--knowledge-store", str(cli_path)])
        # CLI path is valid directory; env path doesn't exist — CLI wins
        assert code != ExitCode.CONFIGURATION_FAILURE


@pytest.mark.cli
@pytest.mark.knowledge
class TestBuildLiveKnowledgeEngine:
    def test_build_accepts_valid_path(self, tmp_path):
        from research_core.cli.providers import build_live_knowledge_engine

        engine = build_live_knowledge_engine(tmp_path)
        assert engine is not None

    def test_build_returns_research_engine(self, tmp_path):
        from research_core.cli.providers import build_live_knowledge_engine
        from research_core.engine import ResearchEngine

        engine = build_live_knowledge_engine(tmp_path)
        assert isinstance(engine, ResearchEngine)

    def test_build_accepts_custom_clock(self, tmp_path):
        from datetime import UTC, datetime

        from research_core.cli.providers import build_live_knowledge_engine

        fixed_ts = datetime(2024, 1, 1, tzinfo=UTC)
        engine = build_live_knowledge_engine(tmp_path, clock=lambda: fixed_ts)
        assert engine is not None


@pytest.mark.cli
@pytest.mark.knowledge
class TestPassThroughProfileProvider:
    def test_resolves_arbitrary_profile_id(self):
        from research_core.cli.providers import _PassThroughProfileProvider

        provider = _PassThroughProfileProvider()
        profile = provider.resolve("marketing")
        assert profile.profile_id == "marketing"

    def test_resolves_any_string(self):
        from research_core.cli.providers import _PassThroughProfileProvider

        provider = _PassThroughProfileProvider()
        for pid in ("default", "custom-profile", "abc123", "some_domain"):
            profile = provider.resolve(pid)
            assert profile.profile_id == pid

    def test_resolve_many_returns_tuple(self):
        from research_core.cli.providers import _PassThroughProfileProvider

        provider = _PassThroughProfileProvider()
        profiles = provider.resolve_many(("a", "b", "c"))
        assert len(profiles) == 3
        assert tuple(p.profile_id for p in profiles) == ("a", "b", "c")
