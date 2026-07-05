"""Agent factory functions.

Each factory returns a configured CrewAI :class:`~crewai.Agent`. Agents are
built lazily (CrewAI is imported inside the functions) and are fully driven by
:class:`~research_team.config.AppConfig`, so operational guard rails such as
``max_rpm`` and per-agent execution timeouts propagate consistently.

The workflow is deliberately *deterministic*: delegation is disabled and agents
communicate strictly through explicit task context (see :mod:`research_team.crew`),
which keeps runs reproducible and easier to debug in production.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import AppConfig, build_llm, build_web_search_tool

if TYPE_CHECKING:  # pragma: no cover - typing only
    from crewai import LLM, Agent
    from crewai_tools import SerperDevTool


def _common_kwargs(config: AppConfig) -> dict[str, Any]:
    """Operational settings shared by every agent."""
    return {
        "verbose": config.verbose,
        "max_rpm": config.max_rpm,
        "max_execution_time": config.request_timeout,
        "allow_delegation": False,
    }


def research_agent(
    config: AppConfig,
    llm: LLM | None = None,
    web_search_tool: SerperDevTool | None = None,
) -> Agent:
    """The web researcher: gathers accurate, up-to-date source material."""
    from crewai import Agent

    llm = llm or build_llm(config)
    web_search_tool = web_search_tool or build_web_search_tool(config)

    return Agent(
        role="Research Agent",
        goal=(
            "Search the web and build accurate, up-to-date research notes for "
            "the given topic, always citing sources."
        ),
        backstory=(
            "You are an OSINT-style internet researcher. You know how to find "
            "trustworthy sources and summarize them without inventing facts."
        ),
        tools=[web_search_tool],
        llm=llm,
        **_common_kwargs(config),
    )


def coding_agent(config: AppConfig, llm: LLM | None = None) -> Agent:
    """The engineer: turns research into practical, runnable examples."""
    from crewai import Agent

    llm = llm or build_llm(config)

    return Agent(
        role="Coding / Analysis Agent",
        goal=(
            "Design small code snippets, scripts, or technical examples that "
            "help the user apply the research in practice."
        ),
        backstory=(
            "You are a senior Python engineer and data analyst. You write "
            "clear, well-commented, runnable code."
        ),
        llm=llm,
        **_common_kwargs(config),
    )


def manager_agent(config: AppConfig, llm: LLM | None = None) -> Agent:
    """The synthesizer: reviews prior work and writes the final report."""
    from crewai import Agent

    llm = llm or build_llm(config)

    return Agent(
        role="Research Manager",
        goal=(
            "Coordinate a research team to deeply answer the user's question "
            "and synthesize a final, production-ready report."
        ),
        backstory=(
            "You are a senior research lead. You review other agents' work and "
            "produce a clear, decisive final deliverable."
        ),
        llm=llm,
        **_common_kwargs(config),
    )
