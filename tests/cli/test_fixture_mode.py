"""Tests for deterministic fixture mode."""

from __future__ import annotations

import json

import pytest

from research_core.cli.app import main
from research_core.cli.exit_codes import ExitCode
from research_core.cli.providers import FIXTURE_PROFILE_IDS, build_fixture_engine


@pytest.mark.cli
class TestFixtureModeEngine:
    def test_engine_has_sources(self):
        from research_core.contracts.request import ResearchRequest

        engine = build_fixture_engine()
        result = engine.run(ResearchRequest(question="fixture test"))
        assert len(result.sources) > 0

    def test_engine_has_evidence(self):
        from research_core.contracts.request import ResearchRequest

        engine = build_fixture_engine()
        result = engine.run(ResearchRequest(question="fixture test"))
        assert len(result.evidence) > 0

    def test_engine_has_ranked_evidence(self):
        from research_core.contracts.request import ResearchRequest

        engine = build_fixture_engine()
        result = engine.run(ResearchRequest(question="fixture test"))
        assert len(result.ranked_evidence) > 0

    def test_engine_has_claims(self):
        from research_core.contracts.request import ResearchRequest

        engine = build_fixture_engine()
        result = engine.run(ResearchRequest(question="fixture test"))
        assert len(result.claims) > 0

    def test_engine_has_gap_analysis(self):
        from research_core.contracts.request import ResearchRequest

        engine = build_fixture_engine()
        result = engine.run(ResearchRequest(question="fixture test"))
        assert result.gap_analysis is not None

    def test_engine_has_synthesis(self):
        from research_core.contracts.request import ResearchRequest

        engine = build_fixture_engine()
        result = engine.run(ResearchRequest(question="fixture test"))
        assert result.synthesis is not None

    def test_fixture_uses_fixed_clock(self):
        from research_core.cli.providers import FIXTURE_CLOCK_TS
        from research_core.contracts.request import ResearchRequest

        engine = build_fixture_engine()
        result = engine.run(ResearchRequest(question="fixture test"))
        assert result.completed_at == FIXTURE_CLOCK_TS


@pytest.mark.cli
class TestFixtureCLI:
    def test_fixture_flag_exits_zero(self, capsys):
        code = main(["run", "test", "--fixture"])
        assert code == ExitCode.SUCCESS

    def test_fixture_markdown_has_heading(self, capsys):
        main(["run", "test", "--fixture"])
        out = capsys.readouterr().out
        assert out.startswith("#")

    def test_fixture_json_has_required_fields(self, capsys):
        main(["run", "test", "--fixture", "--format", "json"])
        data = json.loads(capsys.readouterr().out)
        required_fields = {"status", "sources", "evidence", "claims", "trace"}
        for field in required_fields:
            assert field in data, f"missing field: {field}"

    def test_fixture_deterministic_markdown(self, capsys):
        main(["run", "fixture determinism", "--fixture"])
        out1 = capsys.readouterr().out
        main(["run", "fixture determinism", "--fixture"])
        out2 = capsys.readouterr().out
        assert out1 == out2

    def test_fixture_deterministic_json(self, capsys):
        main(["run", "fixture determinism", "--fixture", "--format", "json"])
        out1 = capsys.readouterr().out
        main(["run", "fixture determinism", "--fixture", "--format", "json"])
        out2 = capsys.readouterr().out
        assert out1 == out2

    def test_fixture_with_web_flag(self, capsys):
        code = main(["run", "test", "--fixture", "--web"])
        assert code == ExitCode.SUCCESS

    def test_fixture_profile_id_recognized(self, capsys):
        code = main(["run", "test", "--fixture", "--profile", "fixture"])
        assert code == ExitCode.SUCCESS

    def test_fixture_profile_ids(self):
        assert "fixture" in FIXTURE_PROFILE_IDS
        assert "default" in FIXTURE_PROFILE_IDS
        assert "demo" in FIXTURE_PROFILE_IDS

    def test_no_fixture_flag_requires_configuration(self, capsys):
        code = main(["run", "test"])
        assert code == ExitCode.CONFIGURATION_FAILURE
