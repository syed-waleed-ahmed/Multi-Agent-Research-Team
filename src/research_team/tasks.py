"""Task factory functions.

Tasks describe *what* each agent must produce and *how* their outputs connect.
The manager task consumes the research and coding tasks as explicit context so
the final report is grounded in the earlier work rather than re-derived.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from crewai import Agent, Task


def research_task(topic: str, agent: Agent) -> Task:
    """Task A — web research producing a structured, sourced brief."""
    from crewai import Task

    return Task(
        name="research",
        description=(
            f"You are the Research Agent.\n"
            f"User topic: {topic}.\n\n"
            "1. Use your web search tool to find recent, reliable information.\n"
            "2. Identify key concepts, trends, pros/cons, and common pitfalls.\n"
            "3. Produce detailed bullet-point research notes with source URLs.\n"
            "4. Keep it factual and avoid making things up."
        ),
        expected_output=(
            "A structured research brief in Markdown with sections: Overview, "
            "Key Points, Important Stats / Facts, Notable Tools / Libraries, "
            "References."
        ),
        agent=agent,
        async_execution=False,
    )


def coding_task(topic: str, agent: Agent) -> Task:
    """Task B — practical code/analysis grounded in the research."""
    from crewai import Task

    return Task(
        name="coding",
        description=(
            f"You are the Coding / Analysis Agent.\n"
            f"User topic: {topic}.\n\n"
            "Using the prior research notes, design one or more short, practical "
            "code examples that help the user apply the ideas. For example: a "
            "Python script demonstrating a key concept, an example API call, or "
            "simple data-analysis/visualization code.\n\n"
            "Explain any non-trivial parts in comments."
        ),
        expected_output=(
            "One or more code blocks plus a short explanation of how the user "
            "can run or adapt the code."
        ),
        agent=agent,
        async_execution=False,
    )


def manager_task(
    topic: str,
    agent: Agent,
    context: Sequence[Task] | None = None,
) -> Task:
    """Task C — the manager synthesizes everything into the final deliverable."""
    from crewai import Task

    kwargs: dict[str, Any] = {
        "name": "synthesis",
        "description": (
            f"You are the Manager Agent, coordinating the multi-agent research "
            f"team.\nUser topic: {topic}.\n\n"
            "You will:\n"
            "1. Review the research notes and code/analysis produced by the "
            "other agents.\n"
            "2. Decide what is relevant to the user's goal.\n"
            "3. Produce a final, user-facing report that is easy to read and "
            "act on."
        ),
        "expected_output": (
            "A polished Markdown report with sections: Problem / Question "
            "Restatement, Summary of Key Findings, Recommended Approach or "
            "Strategy, Code / Technical Implementation Notes, Further Reading / "
            "References."
        ),
        "agent": agent,
        "markdown": True,
        "async_execution": False,
    }
    # Only wire context when provided so we rely on CrewAI's own default sentinel
    # rather than forcing an explicit ``None``.
    if context:
        kwargs["context"] = list(context)
    return Task(**kwargs)
