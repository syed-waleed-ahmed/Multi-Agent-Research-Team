# src/tasks.py
from __future__ import annotations
from crewai import Task

from crewai import Agent


def research_task(topic: str, agent: Agent) -> Task:
    """
    Task A: Web research.
    """
    return Task(
        description=f"""
You are the Research Agent.
User topic: {topic}.

1. Use your web search tool to find recent, reliable information.
2. Identify key concepts, trends, pros/cons, and common pitfalls.
3. Produce detailed bullet-point research notes with source URLs.
4. Keep it factual and avoid making things up.
""".strip(),
        expected_output=(
            "A structured research brief in Markdown with sections: Overview, "
            "Key Points, Important Stats / Facts, Notable Tools / Libraries, "
            "References."
        ),
        agent=agent,
        async_execution=False,
    )


def coding_task(topic: str, agent: Agent) -> Task:
    """
    Task B: Coding/analysis based on the research.
    """
    return Task(
        description=f"""
You are the Coding / Analysis Agent.
User topic: {topic}.

Using the prior research notes, design one or more short, practical code
examples that help the user apply the ideas.

Examples of what you might do:
- Python script that demonstrates a key concept
- Example of calling an API
- Simple data analysis or visualization code

Explain any non-trivial parts in comments.
""".strip(),
        expected_output=(
            "One or more code blocks plus a short explanation of how the user "
            "can run or adapt the code."
        ),
        agent=agent,
        async_execution=False,
    )


def manager_task(topic: str, agent: Agent) -> Task:
    """
    Task C: Manager synthesizes everything into a final deliverable.
    """
    return Task(
        description=f"""
You are the Manager Agent, coordinating the multi-agent research team.
User topic: {topic}.

You will:
1. Review the research notes and code/analysis produced by other agents.
2. Decide what is relevant to the user's goal.
3. Produce a final, user-facing report.

The user wants something they can quickly read and act on.
""".strip(),
        expected_output=(
            "A polished Markdown report with sections: Problem / Question "
            "Restatement, Summary of Key Findings, Recommended Approach or "
            "Strategy, Code / Technical Implementation Notes, Further Reading / "
            "References."
        ),
        agent=agent,
        async_execution=False,
    )
