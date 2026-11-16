"""Tests for the command-line interface (argument parsing, exit codes, streams)."""

from __future__ import annotations

import pytest

from research_team import cli
from research_team.crew import ResearchResult
from research_team.exceptions import RateLimitExceededError, WorkflowError


def _fake_result(report="# Report") -> ResearchResult:
    return ResearchResult(
        topic="x",
        report=report,
        model="openai/gpt-oss-120b",
        duration_seconds=0.5,
        token_usage={"total_tokens": 42},
        document=report + "\n\n## Research Methodology",
    )


@pytest.fixture
def valid_env(monkeypatch, clean_env):
    monkeypatch.setenv("GROQ_API_KEY", "gk")
    monkeypatch.setenv("SERPER_API_KEY", "sk")


def _patch_workflow(monkeypatch, fn):
    monkeypatch.setattr("research_team.crew.run_research_workflow", fn)


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


def test_happy_path_prints_only_report_to_stdout(monkeypatch, valid_env, capsys):
    _patch_workflow(monkeypatch, lambda topic, config, options, on_progress: _fake_result())
    assert cli.main(["--topic", "multi-agent systems", "--quiet"]) == cli.EXIT_OK
    captured = capsys.readouterr()
    assert captured.out.strip() == "# Report"


def test_output_file_contains_full_document(monkeypatch, valid_env, tmp_path):
    _patch_workflow(
        monkeypatch, lambda topic, config, options, on_progress: _fake_result("# Saved Report")
    )
    out = tmp_path / "nested" / "report.md"

    rc = cli.main(["--topic", "x", "--output", str(out), "--quiet"])

    assert rc == cli.EXIT_OK
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Saved Report")
    assert "## Research Methodology" in text


def test_config_error_returns_config_exit_code(monkeypatch, clean_env, capsys):
    # clean_env removes keys and disables .env loading -> config is invalid.
    rc = cli.main(["--topic", "x"])
    assert rc == cli.EXIT_CONFIG_ERROR
    captured = capsys.readouterr()
    assert "GROQ_API_KEY" in captured.err  # errors go to stderr...
    assert "GROQ_API_KEY" not in captured.out  # ...never to stdout


def test_workflow_error_returns_workflow_exit_code(monkeypatch, valid_env, capsys):
    def boom(topic, config, options, on_progress):
        raise WorkflowError("kaboom")

    _patch_workflow(monkeypatch, boom)
    assert cli.main(["--topic", "x", "--quiet"]) == cli.EXIT_WORKFLOW_ERROR
    assert "kaboom" in capsys.readouterr().err


def test_rate_limit_returns_workflow_exit_code(monkeypatch, valid_env):
    def boom(topic, config, options, on_progress):
        raise RateLimitExceededError("slow down")

    _patch_workflow(monkeypatch, boom)
    assert cli.main(["--topic", "x", "--quiet"]) == cli.EXIT_WORKFLOW_ERROR


def test_cli_overrides_reach_config_and_options(monkeypatch, valid_env):
    captured = {}

    def capture(topic, config, options, on_progress):
        captured.update(config=config, options=options)
        return _fake_result()

    _patch_workflow(monkeypatch, capture)
    argv = ["--topic", "x", "--quiet", "--model", "openai/gpt-oss-20b", "--temperature", "0.9"]
    argv += ["--max-tokens", "1536", "--depth", "deep", "--style", "tutorial"]
    argv += ["--workflow-timeout", "120"]
    cli.main(argv)

    cfg, opts = captured["config"], captured["options"]
    assert cfg.temperature == 0.9
    assert cfg.max_tokens == 1536
    assert cfg.workflow_timeout == 120
    assert opts.model == "openai/gpt-oss-20b"
    assert opts.depth == "deep"
    assert opts.report_style == "tutorial"


@pytest.mark.parametrize(
    ("argv", "env", "expected"),
    [
        (["--log-level", "ERROR"], "DEBUG", "ERROR"),
        (["--verbose"], "ERROR", "DEBUG"),
        ([], "warning", "WARNING"),
        ([], None, "INFO"),
    ],
)
def test_log_level_precedence(argv, env, expected):
    args = cli.build_parser().parse_args(["--topic", "x", *argv])
    assert cli._resolve_log_level(args, env) == expected


def test_log_level_env_is_applied(monkeypatch, valid_env):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    seen = {}
    monkeypatch.setattr(cli, "configure_logging", lambda level, quiet: seen.update(level=level))
    _patch_workflow(monkeypatch, lambda topic, config, options, on_progress: _fake_result())
    cli.main(["--topic", "x"])
    assert seen["level"] == "WARNING"
