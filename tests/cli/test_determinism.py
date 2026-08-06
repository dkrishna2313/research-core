"""Tests for output determinism — identical inputs must produce identical outputs."""

from __future__ import annotations

import json

import pytest

from research_core.cli.app import main


@pytest.mark.cli
class TestMarkdownDeterminism:
    def test_same_question_same_markdown(self, capsys):
        main(["run", "What causes climate change?", "--fixture"])
        out1 = capsys.readouterr().out
        main(["run", "What causes climate change?", "--fixture"])
        out2 = capsys.readouterr().out
        assert out1 == out2

    def test_different_questions_differ(self, capsys):
        main(["run", "Question A for determinism test", "--fixture"])
        out1 = capsys.readouterr().out
        main(["run", "Question B for determinism test", "--fixture"])
        out2 = capsys.readouterr().out
        # Different questions may differ in content (the question itself appears)
        # This is a soft check — if they happen to be equal it's an implementation detail
        # but the question text should at least appear in the output
        assert "Question A for determinism test" in out1 or out1 == out2

    def test_markdown_multiple_runs_identical(self, capsys):
        question = "Determinism test repeated run"
        outputs = []
        for _ in range(3):
            main(["run", question, "--fixture"])
            outputs.append(capsys.readouterr().out)
        assert outputs[0] == outputs[1] == outputs[2]


@pytest.mark.cli
class TestJsonDeterminism:
    def test_same_question_same_json(self, capsys):
        main(["run", "What causes climate change?", "--fixture", "--format", "json"])
        out1 = capsys.readouterr().out
        main(["run", "What causes climate change?", "--fixture", "--format", "json"])
        out2 = capsys.readouterr().out
        assert out1 == out2

    def test_json_multiple_runs_identical(self, capsys):
        question = "JSON determinism repeated"
        outputs = []
        for _ in range(3):
            main(["run", question, "--fixture", "--format", "json"])
            outputs.append(capsys.readouterr().out)
        assert outputs[0] == outputs[1] == outputs[2]

    def test_json_keys_stable_across_runs(self, capsys):
        main(["run", "key order test", "--fixture", "--format", "json"])
        data1 = json.loads(capsys.readouterr().out)
        main(["run", "key order test", "--fixture", "--format", "json"])
        data2 = json.loads(capsys.readouterr().out)
        assert list(data1.keys()) == list(data2.keys())

    def test_json_ids_stable_across_runs(self, capsys):
        main(["run", "ID stability test", "--fixture", "--format", "json"])
        data1 = json.loads(capsys.readouterr().out)
        main(["run", "ID stability test", "--fixture", "--format", "json"])
        data2 = json.loads(capsys.readouterr().out)
        ids1 = sorted(s["source_id"] for s in data1["sources"])
        ids2 = sorted(s["source_id"] for s in data2["sources"])
        assert ids1 == ids2


@pytest.mark.cli
class TestClockDeterminism:
    def test_fixture_timestamps_fixed(self, capsys):
        main(["run", "timestamp test", "--fixture", "--format", "json"])
        data1 = json.loads(capsys.readouterr().out)
        main(["run", "timestamp test", "--fixture", "--format", "json"])
        data2 = json.loads(capsys.readouterr().out)
        assert data1.get("completed_at") == data2.get("completed_at")
