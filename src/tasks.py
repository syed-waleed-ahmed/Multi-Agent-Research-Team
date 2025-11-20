# src/tasks.py
from __future__ import annotations
from crewai import Task

from .agents import manager_agent, research_agent, coding_agent


def research_task(topic: str | None = None) -> Task:
    """
    Task A: Web research.
    The `topic` is passed in via crew.kickoff(inputs={"topic": ...}).
    """
    return Task(
        description=(
            "You are the Research Agent.\n"
            "User topic: '{topic}'.\n\n"
            "1. Use your web search tool to find recent, reliable information.\n"
            "2. Identify key concepts, trends, pros/cons, and common pitfalls.\n"
            "3. Produce detailed bullet-point research notes, with inline source hints.\n"
            "4. Keep it factual and avoid making things up."
        ),
        expected_output=(
            "A structured research brief in Markdown with sections:\n"
            "- Overview\n- Key Points\n- Important Stats / Facts\n"
            "- Notable Tools / Libraries\n- References (links or source names)"
        ),
        agent=research_agent(),
        async_execution=False,
    )


def coding_task(topic: str | None = None) -> Task:
    """
    Task B: Coding/analysis based on the research.
    """
    return Task(
        description=(
            "You are the Coding / Analysis Agent.\n"
            "User topic: '{topic}'.\n\n"
            "Using the prior research notes (if provided by the manager), "
            "design one or more short, practical code examples that help the "
            "user apply the ideas.\n\n"
            "Examples of what you might do:\n"
            "- Python script that demonstrates a key concept\n"
            "- Example of calling an API\n"
            "- Simple data analysis or visualization code\n\n"
            "Explain any non-trivial parts in comments."
        ),
        expected_output=(
            "One or more code blocks (preferably Python) plus a short explanation "
            "of how the user can run or adapt the code."
        ),
        agent=coding_agent(),
        async_execution=False,
    )


def manager_task(topic: str | None = None) -> Task:
    """
    Task C: Manager synthesizes everything into a final deliverable.
    """
    return Task(
        description=(
            "You are the Manager Agent, coordinating the multi-agent research team.\n"
            "User topic: '{topic}'.\n\n"
            "You will:\n"
            "1. Review the research notes and code/analysis produced by other agents.\n"
            "2. Decide what is relevant to the user's goal.\n"
            "3. Produce a final, user-facing report.\n\n"
            "The user wants something they can quickly read and act on."
        ),
        expected_output=(
            "A polished Markdown report with sections:\n"
            "1. Problem / Question Restatement\n"
            "2. Summary of Key Findings\n"
            "3. Recommended Approach or Strategy\n"
            "4. Code / Technical Implementation Notes (referencing the Coding Agent's work)\n"
            "5. Further Reading / References"
        ),
        agent=manager_agent(),
        async_execution=False,
    )
