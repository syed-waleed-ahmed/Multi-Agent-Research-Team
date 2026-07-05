"""Tests for the command-line interface (argument parsing, exit codes, wiring)."""

from __future__ import annotations

import pytest

from research_team import cli
from research_team.crew import ResearchResult
from research_team.exceptions import RateLimitExceededError, WorkflowError


def _fake_result(report="# Report") -> ResearchResult:
    return ResearchResult(
        topic="x",
        report=report,
        model="llama-3.1-8b-instant",
        duration_seconds=0.5,
        token_usage={"total_tokens": 42},
    )


@pytest.fixture
def valid_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gk")
    monkeypatch.setenv("SERPER_API_KEY", "sk")


def test_version_exits_zero():
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0


def test_missing_topic_errors():
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code == 2  # argparse usage error


def test_happy_path_returns_zero(monkeypatch, valid_env):
    monkeypatch.setattr(
        "research_team.crew.run_research_workflow",
        lambda topic, config: _fake_result(),
    )
    assert cli.main(["--topic", "multi-agent systems", "--quiet"]) == cli.EXIT_OK


def test_output_file_is_written(monkeypatch, valid_env, tmp_path):
    monkeypatch.setattr(
        "research_team.crew.run_research_workflow",
        lambda topic, config: _fake_result(report="# Saved Report"),
    )
    out = tmp_path / "nested" / "report.md"

    rc = cli.main(["--topic", "x", "--output", str(out), "--quiet"])

    assert rc == cli.EXIT_OK
    assert out.read_text(encoding="utf-8") == "# Saved Report"


def test_config_error_returns_config_exit_code(monkeypatch, clean_env):
    # clean_env removes keys and disables .env loading -> config is invalid.
    rc = cli.main(["--topic", "x"])
    assert rc == cli.EXIT_CONFIG_ERROR


def test_workflow_error_returns_workflow_exit_code(monkeypatch, valid_env):
    def boom(topic, config):
        raise WorkflowError("kaboom")

    monkeypatch.setattr("research_team.crew.run_research_workflow", boom)
    assert cli.main(["--topic", "x", "--quiet"]) == cli.EXIT_WORKFLOW_ERROR


def test_rate_limit_returns_workflow_exit_code(monkeypatch, valid_env):
    def boom(topic, config):
        raise RateLimitExceededError("slow down")

    monkeypatch.setattr("research_team.crew.run_research_workflow", boom)
    assert cli.main(["--topic", "x", "--quiet"]) == cli.EXIT_WORKFLOW_ERROR


def test_cli_overrides_reach_config(monkeypatch, valid_env):
    captured = {}

    def capture(topic, config):
        captured["config"] = config
        return _fake_result()

    monkeypatch.setattr("research_team.crew.run_research_workflow", capture)
    cli.main(
        [
            "--topic",
            "x",
            "--quiet",
            "--model",
            "llama-3.3-70b-versatile",
            "--temperature",
            "0.9",
            "--max-tokens",
            "2048",
        ]
    )

    cfg = captured["config"]
    assert cfg.groq_model == "llama-3.3-70b-versatile"
    assert cfg.temperature == 0.9
    assert cfg.max_tokens == 2048
