# src/main.py
from __future__ import annotations
import argparse
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Multi-Agent Research Team (Research + Coding + Manager agents)",
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Research topic or user goal, e.g. 'Using LlamaIndex for multi-agent research'",
    )
    parser.add_argument(
        "--output",
        help="Optional file path to save the final Markdown report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    topic = args.topic.strip()

    if not topic:
        parser.error("--topic cannot be empty")

    try:
        from .crew import run_research_workflow

        console.rule("[bold cyan]Multi-Agent Research Team[/bold cyan]")
        console.print(f"[bold]Topic:[/bold] {topic}\n")

        result = run_research_workflow(topic)
    except ModuleNotFoundError as exc:
        dependency_name = getattr(exc, "name", "the required Python package")
        console.print(
            f"[bold red]Error:[/bold red] Missing dependency: {dependency_name}. "
            "Install the project requirements before running the workflow."
        )
        return 1
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        return 1

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        console.print(f"[bold green]Saved report to:[/bold green] {output_path}\n")

    console.print("\n[bold green]Final Output:[/bold green]\n")
    console.print(Markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
