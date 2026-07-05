"""Workflow orchestration.

This module wires the agents and tasks into a deterministic, *sequential*
CrewAI pipeline and exposes a single high-level entry point,
:func:`run_research_workflow`, that returns a structured :class:`ResearchResult`.

Resilience
----------
Model providers routinely return transient errors (rate limits, timeouts,
5xx). The workflow retries these with exponential backoff and translates
terminal failures into the package's typed exceptions so that callers can react
appropriately instead of parsing provider error strings.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .agents import coding_agent, manager_agent, research_agent
from .config import AppConfig, build_llm, build_web_search_tool, get_config
from .exceptions import RateLimitExceededError, WorkflowError
from .logging_config import get_logger
from .tasks import coding_task, manager_task, research_task

if TYPE_CHECKING:  # pragma: no cover - typing only
    from crewai import Crew

log = get_logger("crew")

# Base delay (seconds) for exponential backoff between retries.
_BASE_RETRY_DELAY = 2.0


@dataclass(frozen=True)
class ResearchResult:
    """Structured output of a single research run.

    Returning a structured object (rather than a bare string) keeps the workflow
    embeddable: an HTTP layer or job runner can serialize the metadata, while the
    CLI simply renders :attr:`report`.
    """

    topic: str
    report: str
    model: str
    duration_seconds: float
    token_usage: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int | None:
        """Total tokens consumed by the run, if reported by the provider."""
        value = self.token_usage.get("total_tokens")
        return int(value) if isinstance(value, (int, float)) else None


def build_crew(topic: str, config: AppConfig) -> Crew:
    """Assemble the sequential research crew for ``topic``.

    A single LLM and a single web-search tool are shared across agents to avoid
    redundant construction; the manager task explicitly depends on the research
    and coding tasks so their outputs feed the final synthesis.
    """
    from crewai import Crew, Process

    _apply_runtime_defaults()

    llm = build_llm(config)
    web_search_tool = build_web_search_tool(config)

    researcher = research_agent(config, llm, web_search_tool)
    coder = coding_agent(config, llm)
    manager = manager_agent(config, llm)

    t_research = research_task(topic, researcher)
    t_coding = coding_task(topic, coder)
    t_manager = manager_task(topic, manager, context=[t_research, t_coding])

    return Crew(
        agents=[researcher, coder, manager],
        tasks=[t_research, t_coding, t_manager],
        process=Process.sequential,
        verbose=config.verbose,
        max_rpm=config.max_rpm,
    )


def run_research_workflow(
    topic: str,
    config: AppConfig | None = None,
) -> ResearchResult:
    """Run the full research workflow and return a :class:`ResearchResult`.

    Parameters
    ----------
    topic:
        The non-empty research topic / user goal.
    config:
        Configuration to use. Defaults to the process-wide configuration built
        from the environment (:func:`~research_team.config.get_config`).

    Raises
    ------
    ValueError
        If ``topic`` is empty.
    ConfigError
        If configuration is missing or invalid.
    RateLimitExceededError
        If the provider keeps rate-limiting after all retries.
    WorkflowError
        For any other terminal failure while running the crew.
    """
    topic = topic.strip()
    if not topic:
        raise ValueError("topic must not be empty.")

    config = config or get_config()
    log.info("Starting research workflow for topic: %s", topic)
    log.debug(
        "Model=%s temperature=%s max_tokens=%s max_retries=%s",
        config.groq_model,
        config.temperature,
        config.max_tokens,
        config.max_retries,
    )

    crew = build_crew(topic, config)
    started = time.perf_counter()
    output = _run_with_retries(
        lambda: crew.kickoff(inputs={"topic": topic}),
        max_retries=config.max_retries,
    )
    duration = time.perf_counter() - started

    result = ResearchResult(
        topic=topic,
        report=_extract_report(output),
        model=config.groq_model,
        duration_seconds=duration,
        token_usage=_extract_token_usage(output),
    )
    log.info(
        "Workflow finished in %.1fs (tokens: %s)",
        result.duration_seconds,
        result.total_tokens if result.total_tokens is not None else "n/a",
    )
    return result


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _apply_runtime_defaults() -> None:
    """Apply privacy- and noise-friendly defaults for a standalone deployment.

    CrewAI emits anonymous telemetry and prints interactive tracing panels by
    default. A standalone production app should not phone home or clutter output
    unless the operator opts in, so we disable both unless already configured.
    """
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")


def _run_with_retries(
    action: Callable[[], Any],
    *,
    max_retries: int,
    sleep: Callable[[float], None] = time.sleep,
    base_delay: float = _BASE_RETRY_DELAY,
) -> Any:
    """Execute ``action`` with exponential backoff on transient provider errors.

    Terminal failures are translated into the package's typed exceptions.
    """
    transient = _transient_error_types()
    rate_limit = _rate_limit_error_type()
    attempt = 0
    while True:
        try:
            return action()
        except transient as exc:  # type: ignore[misc]
            attempt += 1
            if attempt > max_retries:
                if rate_limit is not None and isinstance(exc, rate_limit):
                    raise RateLimitExceededError(
                        "The model provider rate-limited the request after "
                        f"{max_retries} retries. Try a lighter model via "
                        "GROQ_MODEL or lower GROQ_MAX_TOKENS."
                    ) from exc
                raise WorkflowError(
                    f"The research workflow failed after {max_retries} retries: {exc}"
                ) from exc
            delay = base_delay * (2 ** (attempt - 1))
            log.warning(
                "Transient error (%s); retry %d/%d in %.1fs",
                type(exc).__name__,
                attempt,
                max_retries,
                delay,
            )
            sleep(delay)
        except (RateLimitExceededError, WorkflowError):
            raise
        except Exception as exc:  # unexpected, non-transient failure
            raise WorkflowError(f"The research workflow failed: {exc}") from exc


def _extract_report(output: Any) -> str:
    """Normalize a CrewAI ``CrewOutput`` (or any result) to report text."""
    raw = getattr(output, "raw", None)
    text = str(raw).strip() if raw else str(output).strip()
    if not text:
        raise WorkflowError("The workflow completed but produced an empty report.")
    return text


def _extract_token_usage(output: Any) -> dict[str, Any]:
    """Best-effort extraction of token-usage metrics from a ``CrewOutput``."""
    usage = getattr(output, "token_usage", None)
    if usage is None:
        return {}
    for attr in ("model_dump", "dict"):
        method = getattr(usage, attr, None)
        if callable(method):
            try:
                return dict(method())
            except Exception:  # pragma: no cover - defensive
                break
    if isinstance(usage, dict):
        return dict(usage)
    return {}


def _transient_error_types() -> tuple[type[BaseException], ...]:
    """Return the LiteLLM exception classes that are safe to retry.

    Resolved lazily and defensively so the package tolerates version drift in
    LiteLLM's exception surface.
    """
    try:
        import litellm.exceptions as le
    except Exception:  # pragma: no cover - litellm always present at runtime
        return ()
    names = (
        "RateLimitError",
        "Timeout",
        "APIConnectionError",
        "ServiceUnavailableError",
        "InternalServerError",
    )
    found = tuple(
        cls
        for name in names
        if isinstance(cls := getattr(le, name, None), type) and issubclass(cls, BaseException)
    )
    return found


def _rate_limit_error_type() -> type[BaseException] | None:
    try:
        from litellm.exceptions import RateLimitError

        return RateLimitError
    except Exception:  # pragma: no cover
        return None
