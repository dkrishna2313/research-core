"""Tests for packaging — LICENSE, version, wheel metadata, console script."""

from __future__ import annotations

import importlib.metadata
import subprocess
from pathlib import Path

import pytest


@pytest.mark.cli
class TestVersion:
    def test_package_version_is_0_8_0(self):
        meta = importlib.metadata.metadata("research-core")
        assert meta["Version"] == "0.8.0"

    def test_init_version_matches(self):
        import research_core

        assert research_core.__version__ == "0.8.0"

    def test_version_consistent(self):
        import research_core

        meta = importlib.metadata.metadata("research-core")
        assert meta["Version"] == research_core.__version__


@pytest.mark.cli
class TestLicense:
    def test_license_file_exists(self):
        repo_root = Path(__file__).parent.parent.parent
        license_path = repo_root / "LICENSE"
        assert license_path.exists(), "LICENSE file must exist at repo root"

    def test_license_file_is_apache_2(self):
        repo_root = Path(__file__).parent.parent.parent
        license_path = repo_root / "LICENSE"
        text = license_path.read_text(encoding="utf-8")
        assert "Apache License" in text
        assert "Version 2.0" in text

    def test_license_metadata(self):
        meta = importlib.metadata.metadata("research-core")
        license_val = meta.get("License") or meta.get("License-Expression") or ""
        assert "Apache" in license_val or "apache" in license_val.lower()


@pytest.mark.cli
class TestConsoleScript:
    def test_research_core_command_exists(self):
        result = subprocess.run(
            ["research-core", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_research_core_version_output(self):
        result = subprocess.run(
            ["research-core", "--version"],
            capture_output=True,
            text=True,
        )
        assert "0.8.0" in result.stdout

    def test_research_core_run_fixture(self):
        result = subprocess.run(
            ["research-core", "run", "test", "--fixture"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_research_core_run_json(self):
        import json

        result = subprocess.run(
            ["research-core", "run", "test", "--fixture", "--format", "json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, dict)
