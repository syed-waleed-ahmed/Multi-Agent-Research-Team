# src/crew.py (only the bottom part needs to change)
from __future__ import annotations

from typing import Dict, Any

from crewai import Crew, Process
from litellm.exceptions import RateLimitError  # ⬅️ add this import

from .agents import manager_agent, research_agent, coding_agent
from .tasks import research_task, coding_task, manager_task
from .config import llm


def build_crew(topic: str) -> Crew:
    manager = manager_agent()
    researcher = research_agent()
    coder = coding_agent()

    tasks = [
        research_task(topic),
        coding_task(topic),
        manager_task(topic),
    ]

    crew = Crew(
        agents=[researcher, coder],   # workers only
        tasks=tasks,
        process=Process.hierarchical,
        manager_agent=manager,
        manager_llm=llm,
        verbose=True,
    )

    return crew


def run_research_workflow(topic: str) -> str:
    crew = build_crew(topic)
    inputs: Dict[str, Any] = {"topic": topic}
    try:
        result = crew.kickoff(inputs=inputs)
        return str(result)
    except RateLimitError as e:
        # Friendly fallback if Groq refuses due to rate limit
        return (
            "❌ Groq rate limit hit for your model.\n\n"
            "Try one or more of these:\n"
            "- Use a lighter model in .env (e.g. GROQ_MODEL=llama-3.1-8b-instant)\n"
            "- Lower max_tokens in src/config.py (e.g. 256 or 512)\n\n"
            f"Technical details:\n{e}"
        )
