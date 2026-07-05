"""Tests for agent and task factories.

These construct real CrewAI objects and are skipped if CrewAI is unavailable.
They make no network calls: the LLM is provided as a model-id string and no
crew is kicked off.
"""

from __future__ import annotations

import pytest

pytest.importorskip("crewai")

from research_team import agents, tasks  # noqa: E402
from research_team.config import AppConfig  # noqa: E402

_STUB_LLM = "groq/llama-3.1-8b-instant"


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(groq_api_key="gk", serper_api_key="sk", verbose=False)


def _bare_agent():
    from crewai import Agent

    return Agent(
        role="Test",
        goal="goal",
        backstory="backstory",
        llm=_STUB_LLM,
        allow_delegation=False,
    )


def test_research_task_embeds_topic():
    task = tasks.research_task("QUANTUM_ERROR_CORRECTION", _bare_agent())
    assert "QUANTUM_ERROR_CORRECTION" in task.description
    assert task.name == "research"
    assert task.async_execution is False


def test_manager_task_wires_context():
    agent = _bare_agent()
    research = tasks.research_task("x", agent)
    coding = tasks.coding_task("x", agent)
    manager = tasks.manager_task("x", agent, context=[research, coding])

    assert manager.context is not None
    assert len(manager.context) == 2


def test_agent_factories_disable_delegation(config):
    coder = agents.coding_agent(config, llm=_STUB_LLM)
    manager = agents.manager_agent(config, llm=_STUB_LLM)

    assert coder.allow_delegation is False
    assert manager.allow_delegation is False
    assert "Manager" in manager.role
