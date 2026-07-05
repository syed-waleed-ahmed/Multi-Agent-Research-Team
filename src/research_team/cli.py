"""Command-line interface.

The CLI is a thin adapter over :func:`research_team.crew.run_research_workflow`.
It parses arguments, configures logging, resolves configuration (with optional
per-invocation overrides), renders the report, and maps typed exceptions to
conventional process exit codes.

Exit codes
----------
* ``0``  success
* ``1``  workflow failure (including rate limiting)
* ``2``  configuration error (missing/invalid settings)
* ``3``  missing dependency
* ``130`` interrupted (Ctrl-C)
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from . import __version__
from .exceptions import ConfigError, DependencyError, RateLimitExceededError, WorkflowError
from .logging_config import configure_logging, get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from rich.console import Console

    from .crew import ResearchResult

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
        help="Optional file path to save the final Markdown report.",
    )

    tuning = parser.add_argument_group("model tuning (overrides .env)")
    tuning.add_argument("--model", help="Groq model id, e.g. 'llama-3.1-8b-instant'.")
    tuning.add_argument("--temperature", type=float, help="Sampling temperature (0.0-2.0).")
    tuning.add_argument("--max-tokens", type=int, help="Maximum tokens per response.")
    tuning.add_argument("--max-rpm", type=int, help="Cap requests-per-minute across the crew.")
    tuning.add_argument("--max-retries", type=int, help="Retries on transient provider errors.")
    tuning.add_argument(
        "--timeout",
        type=int,
        dest="request_timeout",
        help="Per-agent execution timeout in seconds.",
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
        help="Explicit log level (default from LOG_LEVEL or INFO).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _resolve_log_level(args: argparse.Namespace) -> str:
    if args.log_level:
        return args.log_level
    if args.verbose:
        return "DEBUG"
    return "INFO"


def run(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and execute the workflow; return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(_resolve_log_level(args), quiet=args.quiet)

    topic = args.topic.strip()
    if not topic:
        parser.error("--topic cannot be empty")

    # Import the heavy workflow lazily so --help/--version stay instant and a
    # missing optional dependency degrades gracefully.
    try:
        from .config import AppConfig
        from .crew import run_research_workflow
    except ModuleNotFoundError as exc:
        raise DependencyError(
            f"Missing dependency: {exc.name}. Install project requirements "
            "(pip install -e .) before running the workflow."
        ) from exc

    try:
        config = AppConfig.from_env().with_overrides(
            groq_model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            max_rpm=args.max_rpm,
            max_retries=args.max_retries,
            request_timeout=args.request_timeout,
            verbose=args.verbose or None,
        )
    except ConfigError as exc:
        _print_error(str(exc), quiet=args.quiet)
        return EXIT_CONFIG_ERROR

    console = _get_console()
    if console is not None and not args.quiet:
        console.rule("[bold cyan]Multi-Agent Research Team[/bold cyan]")
        console.print(f"[bold]Topic:[/bold] {topic}\n")

    try:
        result = run_research_workflow(topic, config)
    except RateLimitExceededError as exc:
        _print_error(str(exc), quiet=args.quiet)
        return EXIT_WORKFLOW_ERROR
    except (WorkflowError, ValueError) as exc:
        _print_error(str(exc), quiet=args.quiet)
        return EXIT_WORKFLOW_ERROR

    if args.output:
        saved_to = _save_report(result.report, args.output)
        if not args.quiet and console is not None:
            console.print(f"[bold green]Saved report to:[/bold green] {saved_to}\n")

    _render_report(result, console, quiet=args.quiet)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Entry point that also handles top-level, cross-cutting failures."""
    try:
        return run(argv)
    except DependencyError as exc:
        _print_error(str(exc), quiet=False)
        return EXIT_DEPENDENCY_ERROR
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        _print_error("Interrupted.", quiet=False)
        return EXIT_INTERRUPTED


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def _get_console() -> Console | None:
    try:
        from rich.console import Console

        return Console()
    except Exception:  # pragma: no cover - rich should be installed
        return None


def _print_error(message: str, *, quiet: bool) -> None:
    console = _get_console()
    if console is not None:
        console.print(f"[bold red]Error:[/bold red] {message}")
    else:  # pragma: no cover - fallback path
        import sys

        print(f"Error: {message}", file=sys.stderr)


def _save_report(report: str, output: str) -> Path:
    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


def _render_report(result: ResearchResult, console: Console | None, *, quiet: bool) -> None:
    if console is None:
        print(result.report)
        return
    if quiet:
        # Machine-friendly: plain report only, no decoration.
        console.print(result.report, markup=False, highlight=False)
        return
    from rich.markdown import Markdown

    console.print("\n[bold green]Final Report:[/bold green]\n")
    console.print(Markdown(result.report))
    if result.total_tokens is not None:
        console.print(
            f"\n[dim]Model: {result.model} | "
            f"{result.total_tokens} tokens | "
            f"{result.duration_seconds:.1f}s[/dim]"
        )


if __name__ == "__main__":
    raise SystemExit(main())
