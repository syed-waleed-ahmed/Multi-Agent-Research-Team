# src/agents.py
from __future__ import annotations

from crewai import Agent, LLM
from crewai_tools import SerperDevTool

from .config import get_llm, get_web_search_tool


def manager_agent(llm: LLM | None = None) -> Agent:
    llm = llm or get_llm()

    return Agent(
        role="Research Manager",
        goal=(
            "Coordinate a research team to deeply answer the user's question "
            "and synthesize a final, production-ready report."
        ),
        backstory=(
            "You are a senior research lead. You break down problems, review "
            "other agents' work, and produce a clear final deliverable."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=True,
    )


def research_agent(
    llm: LLM | None = None,
    web_search_tool: SerperDevTool | None = None,
) -> Agent:
    llm = llm or get_llm()
    web_search_tool = web_search_tool or get_web_search_tool()

    return Agent(
        role="Research Agent",
        goal=(
            "Search the web and build accurate, up-to-date research notes for "
            "the given topic."
        ),
        backstory=(
            "You are an OSINT-style internet researcher. You know how to find "
            "trustworthy sources and summarize them."
        ),
        tools=[web_search_tool],
        llm=llm,
        verbose=True,
    )


def coding_agent(llm: LLM | None = None) -> Agent:
    llm = llm or get_llm()

    return Agent(
        role="Coding / Analysis Agent",
        goal=(
            "Design small code snippets, scripts, or technical examples that "
            "help the user apply the research in practice."
        ),
        backstory=(
            "You are a senior Python engineer and data analyst. You write "
            "clear, well-commented code."
        ),
        llm=llm,
        verbose=True,
    )
