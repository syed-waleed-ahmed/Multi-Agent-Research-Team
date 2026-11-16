"""End-to-end test server: the real web app with a deterministic fake engine.

This file lives under ``tests/`` on purpose — the fake engine is test-only and
never ships in the package. Playwright starts it via ``frontend/playwright.config.ts``.

The fake runner emits the same ProgressEvents as the real engine and honours
cancellation. Scenarios are selected by markers in the topic:

* default          — succeeds (~0.4 s per stage)
* ``[slow]``       — ~2.5 s per stage (lets tests cancel a running job)
* ``[rate-limit]`` — a retry event, then a provider rate-limit failure
* ``[provider-down]`` — the provider rejects the request

Usage: ``python tests/e2e/server.py`` (env: ``E2E_PORT``, default 8765).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from research_team.config import AppConfig  # noqa: E402
from research_team.crew import ResearchResult  # noqa: E402
from research_team.exceptions import ProviderUnavailableError, RateLimitExceededError  # noqa: E402
from research_team.progress import STAGES, EventType, ProgressEvent, Stage  # noqa: E402
from research_team.report import (  # noqa: E402
    assemble_document,
    build_methodology,
    build_sources_section,
    check_citations,
)
from research_team.search import SearchResult  # noqa: E402

SOURCES = (
    SearchResult(
        title="Official documentation",
        url="https://docs.example.org/guide",
        snippet="An authoritative overview of the topic.",
        published="2026-03-01",
        provider="serper",
        query="overview",
    ),
    SearchResult(
        title="Engineering blog post",
        url="https://blog.example.com/post",
        snippet="Practical lessons from production.",
        provider="serper",
        query="best practices",
    ),
)


def _report(topic: str) -> str:
    return (
        f"# {topic}\n\n## Executive Summary\nA concise summary for **{topic}**.\n\n"
        "## Key Findings\n- Finding backed by [the docs](https://docs.example.org/guide)\n"
        "- A claim with an [unretrieved link](https://unverified.example.net/page)\n\n"
        "## Technical Implementation Notes\n```python\nprint('hello')\n```\n\n"
        "## References\n- [Official documentation](https://docs.example.org/guide)\n"
    )


def fake_runner(topic, config, options, *, on_progress, control, max_report_chars):  # noqa: ANN001
    delay = 2.5 if "[slow]" in topic else 0.4
    started = time.perf_counter()
    on_progress(
        ProgressEvent(
            EventType.RUN_STARTED,
            None,
            "Research run started",
            {"provider": "groq", "model": options.model},
        )
    )
    for stage in STAGES:
        on_progress(
            ProgressEvent(
                EventType.STAGE_STARTED,
                stage,
                f"{stage.agent_name} started",
                {"provider": "groq", "model": options.model, "attempt": 1},
            )
        )
        on_progress(ProgressEvent(EventType.LLM_CALL, stage, "Model request sent", {"attempt": 1}))
        if stage is Stage.RESEARCH:
            if "[rate-limit]" in topic:
                on_progress(
                    ProgressEvent(
                        EventType.RETRY,
                        stage,
                        "Provider rate limited; retrying in 1s",
                        {
                            "attempt": 1,
                            "max_retries": 1,
                            "delay_seconds": 1.0,
                            "rate_limited": True,
                        },
                    )
                )
                control.wait(0.5)
                on_progress(
                    ProgressEvent(
                        EventType.STAGE_FAILED,
                        stage,
                        "Research Agent stopped",
                        {"error_type": "RateLimitExceededError"},
                    )
                )
                raise RateLimitExceededError("fake rate limit")
            if "[provider-down]" in topic:
                on_progress(
                    ProgressEvent(
                        EventType.STAGE_FAILED,
                        stage,
                        "Research Agent stopped",
                        {"error_type": "ProviderUnavailableError"},
                    )
                )
                raise ProviderUnavailableError("fake provider outage")
            for source in SOURCES:
                on_progress(
                    ProgressEvent(
                        EventType.SEARCH,
                        stage,
                        f"Searched: {source.query}",
                        {"query": source.query, "results": 5, "ok": True},
                    )
                )
        control.wait(delay)
        on_progress(
            ProgressEvent(
                EventType.STAGE_COMPLETED,
                stage,
                f"{stage.agent_name} finished",
                {"duration_seconds": delay, "output_chars": 100},
            )
        )
    report = _report(topic)
    citations = check_citations(report, SOURCES)
    methodology = build_methodology(
        model=options.model,
        provider="Groq",
        queries=[s.query for s in SOURCES],
        sources=SOURCES,
        stage_durations={s.value: delay for s in STAGES},
        citation_check=citations,
        search_provider="serper",
    )
    on_progress(ProgressEvent(EventType.RUN_COMPLETED, None, "Report ready", {}))
    return ResearchResult(
        topic=topic,
        report=report,
        model=options.model,
        duration_seconds=time.perf_counter() - started,
        token_usage={"total_tokens": 1234},
        provider="Groq",
        research_notes="## Overview\nResearch notes.",
        code_examples="```python\nprint('hello')\n```",
        sources=SOURCES,
        search_queries=tuple(s.query for s in SOURCES),
        citation_check=citations,
        methodology=methodology,
        document=assemble_document(
            report, sources_section=build_sources_section(SOURCES), methodology=methodology
        ),
        stage_durations={s.value: delay for s in STAGES},
    )


def main() -> None:
    import uvicorn

    from research_team.web.app import create_app
    from research_team.web.settings import WebSettings

    dist = ROOT / "frontend" / "dist"
    settings = WebSettings(
        database_url="sqlite://",
        static_dir=dist if (dist / "index.html").is_file() else None,
        jobs_per_ip_per_hour=int(os.getenv("E2E_JOBS_PER_HOUR", "100")),
        jobs_per_ip_per_day=int(os.getenv("E2E_JOBS_PER_DAY", "200")),
        global_jobs_per_day=1000,
        api_requests_per_ip_per_minute=10_000,
        max_queued_jobs=20,
        result_cache_ttl_hours=0,
        ip_hash_salt="e2e",
    )
    config = AppConfig(groq_api_key="e2e-not-a-real-key", serper_api_key="e2e-not-a-real-key")
    app = create_app(settings, config=config, runner=fake_runner)
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("E2E_PORT", "8765")), log_level="warning")


if __name__ == "__main__":
    main()
