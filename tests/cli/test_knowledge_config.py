"""Tests for knowledge-store configuration utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from research_core.cli.config import (
    KNOWLEDGE_STORE_ENV,
    resolve_knowledge_store,
    validate_knowledge_store,
)


@pytest.mark.cli
class TestKnowledgeStoreEnvConstant:
    def test_env_constant_value(self):
        assert KNOWLEDGE_STORE_ENV == "RESEARCH_CORE_KNOWLEDGE_STORE"


@pytest.mark.cli
class TestResolveKnowledgeStore:
    def test_returns_none_when_no_cli_arg_and_no_env(self, monkeypatch):
        monkeypatch.delenv(KNOWLEDGE_STORE_ENV, raising=False)
        assert resolve_knowledge_store(None) is None

    def test_returns_path_from_env_when_no_cli_arg(self, monkeypatch, tmp_path):
        monkeypatch.setenv(KNOWLEDGE_STORE_ENV, str(tmp_path))
        result = resolve_knowledge_store(None)
        assert result == tmp_path

    def test_cli_arg_wins_over_env(self, monkeypatch, tmp_path):
        env_path = tmp_path / "env_store"
        cli_path = tmp_path / "cli_store"
        monkeypatch.setenv(KNOWLEDGE_STORE_ENV, str(env_path))
        result = resolve_knowledge_store(str(cli_path))
        assert result == cli_path

    def test_cli_arg_used_when_env_absent(self, monkeypatch, tmp_path):
        monkeypatch.delenv(KNOWLEDGE_STORE_ENV, raising=False)
        result = resolve_knowledge_store(str(tmp_path))
        assert result == tmp_path

    def test_returns_path_type_from_cli_arg(self, monkeypatch, tmp_path):
        monkeypatch.delenv(KNOWLEDGE_STORE_ENV, raising=False)
        result = resolve_knowledge_store(str(tmp_path))
        assert isinstance(result, Path)

    def test_returns_path_type_from_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv(KNOWLEDGE_STORE_ENV, str(tmp_path))
        result = resolve_knowledge_store(None)
        assert isinstance(result, Path)

    def test_cli_arg_none_and_env_unset_returns_none(self, monkeypatch):
        monkeypatch.delenv(KNOWLEDGE_STORE_ENV, raising=False)
        assert resolve_knowledge_store(None) is None


@pytest.mark.cli
class TestValidateKnowledgeStore:
    def test_returns_none_for_valid_directory(self, tmp_path):
        assert validate_knowledge_store(tmp_path) is None

    def test_returns_error_for_nonexistent_path(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist"
        result = validate_knowledge_store(nonexistent)
        assert result is not None
        assert "does not exist" in result

    def test_returns_error_for_file_not_directory(self, tmp_path):
        file_path = tmp_path / "somefile.txt"
        file_path.write_text("hello")
        result = validate_knowledge_store(file_path)
        assert result is not None
        assert "not a directory" in result

    def test_nonexistent_error_contains_path(self, tmp_path):
        nonexistent = tmp_path / "missing_store"
        result = validate_knowledge_store(nonexistent)
        assert str(nonexistent) in (result or "")

    def test_file_error_contains_path(self, tmp_path):
        file_path = tmp_path / "notadir.txt"
        file_path.write_text("x")
        result = validate_knowledge_store(file_path)
        assert str(file_path) in (result or "")
