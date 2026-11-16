"""Command-line interface.

The CLI is a thin adapter over :func:`research_team.crew.run_research_workflow`.
It parses arguments, configures logging, resolves configuration (with optional
per-invocation overrides), renders the report, and maps typed exceptions to
conventional process exit codes.

Output streams
--------------
The report is written to **stdout**; logs, progress and errors go to
**stderr**. ``multi-agent-research-team --topic X --quiet > report.md`` therefore
captures only the report.

Exit codes
----------
* ``0``  success
* ``1``  workflow failure (including rate limiting, cancellation and timeouts)
* ``2``  configuration error (missing/invalid settings)
* ``3``  missing dependency
* ``130`` interrupted (Ctrl-C)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from . import __version__
from .exceptions import ConfigError, DependencyError, WorkflowError
from .logging_config import configure_logging, get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from rich.console import Console

    from .crew import ResearchResult
    from .progress import ProgressEvent

log = get_logger("cli")

EXIT_OK = 0
EXIT_WORKFLOW_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_DEPENDENCY_ERROR = 3
EXIT_INTERRUPTED = 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="multi-agent-research-team",
        description=(
            "Coordinate a team of AI agents (research, coding, manager) to "
            "research a topic and produce a professional Markdown report."
        ),
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Research topic or user goal, e.g. 'Using CrewAI for multi-agent research'.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Optional file path to save the final Markdown document.",
    )

    research = parser.add_argument_group("research options")
    research.add_argument(
        "--depth",
        choices=["quick", "standard", "deep"],
        default="standard",
        help="How much web searching to do (default: standard).",
    )
    research.add_argument(
        "--style",
        dest="report_style",
        choices=["technical_report", "executive_brief", "tutorial"],
        default="technical_report",
        help="Shape of the final report (default: technical_report).",
    )
    research.add_argument("--instructions", help="Extra guidance, e.g. audience or focus areas.")

    tuning = parser.add_argument_group("model tuning (overrides .env)")
    tuning.add_argument(
        "--provider",
        choices=["groq", "gemini", "openrouter", "openai_compatible", "ollama"],
        help="LLM provider (default from LLM_PROVIDER or groq).",
    )
    tuning.add_argument("--model", help="Model id for the provider, e.g. 'llama-3.1-8b-instant'.")
    tuning.add_argument("--temperature", type=float, help="Sampling temperature (0.0-2.0).")
    tuning.add_argument("--max-tokens", type=int, help="Maximum tokens per response.")
    tuning.add_argument("--max-rpm", type=int, help="Cap requests-per-minute across the crew.")
    tuning.add_argument(
        "--max-retries", type=int, help="Retries for a single failed model request."
    )
    tuning.add_argument(
        "--timeout",
        type=int,
        dest="request_timeout",
        help="Per-agent execution timeout in seconds.",
    )
    tuning.add_argument(
        "--workflow-timeout",
        type=int,
        help="Wall-clock budget for the whole run in seconds.",
    )

    output = parser.add_argument_group("output & logging")
    output.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose agent/crew tracing and DEBUG logs.",
    )
    output.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress logs and status output; print only the report.",
    )
    output.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Explicit log level (default: LOG_LEVEL from the environment, else INFO).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _resolve_log_level(args: argparse.Namespace, env_level: str | None = None) -> str:
    """Precedence: --log-level, then --verbose, then LOG_LEVEL, then INFO."""
    if args.log_level:
        return str(args.log_level)
    if args.verbose:
        return "DEBUG"
    if env_level and env_level.strip():
        return env_level.strip().upper()
    return "INFO"


def run(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and execute the workflow; return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    topic = args.topic.strip()
    if not topic:
        parser.error("--topic cannot be empty")

    # Import the heavy workflow lazily so --help/--version stay instant and a
    # missing optional dependency degrades gracefully.
    try:
        from .config import AppConfig, load_environment
        from .crew import ResearchOptions, run_research_workflow
    except ModuleNotFoundError as exc:
        raise DependencyError(
            f"Missing dependency: {exc.name}. Install project requirements "
            "(pip install -e .) before running the workflow."
        ) from exc

    # Load .env first so LOG_LEVEL from the file is honoured before any logging.
    load_environment()
    configure_logging(_resolve_log_level(args, os.getenv("LOG_LEVEL")), quiet=args.quiet)

    try:
        config = AppConfig.from_env(load_dotenv_file=False).with_overrides(
            llm_provider=args.provider,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            max_rpm=args.max_rpm,
            max_retries=args.max_retries,
            request_timeout=args.request_timeout,
            workflow_timeout=args.workflow_timeout,
            verbose=args.verbose or None,
        )
        options = ResearchOptions(
            depth=args.depth,
            report_style=args.report_style,
            instructions=args.instructions,
            model=args.model,
        )
        options.validate()
    except (ConfigError, ValueError) as exc:
        _print_error(str(exc))
        return EXIT_CONFIG_ERROR

    console = _get_console(stderr=True)
    if console is not None and not args.quiet:
        console.rule("[bold cyan]Multi-Agent Research Team[/bold cyan]")
        console.print(f"[bold]Topic:[/bold] {topic}\n")

    try:
        result = run_research_workflow(
            topic,
            config,
            options,
            on_progress=None if args.quiet else _log_progress,
        )
    except (WorkflowError, ValueError) as exc:
        _print_error(str(exc))
        return EXIT_WORKFLOW_ERROR

    if args.output:
        saved_to = _save_report(result.document or result.report, args.output)
        if not args.quiet and console is not None:
            console.print(f"[bold green]Saved report to:[/bold green] {saved_to}\n")

    _render_report(result, quiet=args.quiet)
    return EXIT_OK


def _ensure_utf8_streams() -> None:
    """Avoid UnicodeEncodeError on legacy (e.g. cp1252) Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        encoding = (getattr(stream, "encoding", "") or "").lower()
        if callable(reconfigure) and encoding not in {"utf-8", "utf8"}:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # pragma: no cover - exotic stream wrappers
                pass


def main(argv: list[str] | None = None) -> int:
    """Entry point that also handles top-level, cross-cutting failures."""
    _ensure_utf8_streams()
    try:
        return run(argv)
    except DependencyError as exc:
        _print_error(str(exc))
        return EXIT_DEPENDENCY_ERROR
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        _print_error("Interrupted.")
        return EXIT_INTERRUPTED


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def _get_console(*, stderr: bool = False) -> Console | None:
    try:
        from rich.console import Console

        return Console(stderr=stderr)
    except Exception:  # pragma: no cover - rich should be installed
        return None


def _print_error(message: str) -> None:
    """Errors always go to stderr so stdout stays reserved for the report."""
    console = _get_console(stderr=True)
    if console is not None:
        console.print(f"[bold red]Error:[/bold red] {message}", markup=True, highlight=False)
    else:  # pragma: no cover - fallback path
        print(f"Error: {message}", file=sys.stderr)


def _log_progress(event: ProgressEvent) -> None:
    stage = f"[{event.stage.agent_name}] " if event.stage else ""
    log.info("%s%s", stage, event.message)


def _save_report(report: str, output: str) -> Path:
    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


def _render_report(result: ResearchResult, *, quiet: bool) -> None:
    console = _get_console()
    if console is None:  # pragma: no cover - rich should be installed
        print(result.report)
        return
    if quiet:
        # Machine-friendly: plain report only, no decoration.
        console.print(result.report, markup=False, highlight=False, soft_wrap=True)
        return
    from rich.markdown import Markdown

    console.print("\n[bold green]Final Report:[/bold green]\n")
    console.print(Markdown(result.report))
    meta = [f"Model: {result.model}"]
    if result.provider:
        meta.append(result.provider)
    if result.total_tokens is not None:
        meta.append(f"{result.total_tokens} tokens")
    meta.append(f"{result.duration_seconds:.1f}s")
    meta.append(f"{len(result.sources)} sources retrieved")
    _get_console(stderr=True).print(f"\n[dim]{' | '.join(meta)}[/dim]")  # type: ignore[union-attr]


if __name__ == "__main__":
    raise SystemExit(main())
