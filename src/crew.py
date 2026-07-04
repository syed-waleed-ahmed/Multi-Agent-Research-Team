from __future__ import annotations

from typing import Any, Dict

from crewai import Crew, Process
from litellm.exceptions import RateLimitError

from .agents import manager_agent, research_agent, coding_agent
from .config import get_llm, get_web_search_tool
from .tasks import coding_task, manager_task, research_task


def build_crew(topic: str) -> Crew:
    llm = get_llm()
    web_search_tool = get_web_search_tool()

    manager = manager_agent(llm)
    researcher = research_agent(llm, web_search_tool)
    coder = coding_agent(llm)

    tasks = [
        research_task(topic, researcher),
        coding_task(topic, coder),
        manager_task(topic, manager),
    ]

    crew = Crew(
        agents=[researcher, coder, manager],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    return crew


def run_research_workflow(topic: str) -> str:
    crew = build_crew(topic)
    inputs: Dict[str, Any] = {"topic": topic}
    try:
        result = crew.kickoff(inputs=inputs)
        if hasattr(result, "raw") and getattr(result, "raw"):
            return str(getattr(result, "raw")).strip()

        return str(result).strip()
    except RateLimitError as e:
        raise RuntimeError(
            "Groq rate limit hit for your model. Try a lighter model in .env "
            "or lower GROQ_MAX_TOKENS."
        ) from e
