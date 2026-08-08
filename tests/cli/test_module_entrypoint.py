"""Tests for python -m research_core.cli module entrypoint."""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.cli
class TestModuleEntrypoint:
    def test_module_version(self):
        result = subprocess.run(
            [sys.executable, "-m", "research_core.cli", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "0.8.1" in result.stdout

    def test_module_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "-m", "research_core.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "research-core" in result.stdout

    def test_module_run_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "research_core.cli", "run", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_module_run_fixture(self):
        result = subprocess.run(
            [sys.executable, "-m", "research_core.cli", "run", "test question", "--fixture"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.startswith("#")

    def test_module_run_fixture_json(self):
        import json

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_core.cli",
                "run",
                "test",
                "--fixture",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, dict)
        assert "status" in data

    def test_module_no_subcommand_exits_2(self):
        result = subprocess.run(
            [sys.executable, "-m", "research_core.cli"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2

    def test_module_unknown_profile_exits_4(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "research_core.cli",
                "run",
                "test",
                "--fixture",
                "--profile",
                "no-such-profile",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 4

    def test_module_stderr_on_error(self):
        result = subprocess.run(
            [sys.executable, "-m", "research_core.cli", "run", "test"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 8
        assert result.stderr != ""
        assert result.stdout == ""
