# src/main.py
from __future__ import annotations
import argparse

from rich.console import Console
from rich.markdown import Markdown

from .crew import run_research_workflow

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Research Team (Manager + Research + Coding agents)"
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Research topic or user goal, e.g. 'Using LlamaIndex for multi-agent research' ",
    )

    args = parser.parse_args()
    topic = args.topic

    console.rule("[bold cyan]Multi-Agent Research Team[/bold cyan]")
    console.print(f"[bold]Topic:[/bold] {topic}\n")

    result = run_research_workflow(topic)

    console.print("\n[bold green]Final Output:[/bold green]\n")
    console.print(Markdown(result))


if __name__ == "__main__":
    main()
