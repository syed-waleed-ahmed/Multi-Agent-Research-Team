# Graph Report - D:\Projects & Stuff\multi-agent-research-team  (2026-07-05)

## Corpus Check
- 16 files · ~23,808 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 165 nodes · 353 edges · 15 communities detected
- Extraction: 55% EXTRACTED · 45% INFERRED · 0% AMBIGUOUS · INFERRED: 160 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]

## God Nodes (most connected - your core abstractions)
1. `AppConfig` - 38 edges
2. `WorkflowError` - 26 edges
3. `RateLimitExceededError` - 24 edges
4. `ConfigError` - 21 edges
5. `ResearchResult` - 16 edges
6. `run()` - 14 edges
7. `main()` - 13 edges
8. `build_crew()` - 12 edges
9. `run_research_workflow()` - 11 edges
10. `_run_with_retries()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Agent factory functions.  Each factory returns a configured CrewAI :class:`~crew` --uses--> `AppConfig`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\research_team\agents.py → D:\Projects & Stuff\multi-agent-research-team\src\research_team\config.py
- `Operational settings shared by every agent.` --uses--> `AppConfig`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\research_team\agents.py → D:\Projects & Stuff\multi-agent-research-team\src\research_team\config.py
- `The web researcher: gathers accurate, up-to-date source material.` --uses--> `AppConfig`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\research_team\agents.py → D:\Projects & Stuff\multi-agent-research-team\src\research_team\config.py
- `The engineer: turns research into practical, runnable examples.` --uses--> `AppConfig`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\research_team\agents.py → D:\Projects & Stuff\multi-agent-research-team\src\research_team\config.py
- `The synthesizer: reviews prior work and writes the final report.` --uses--> `AppConfig`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\research_team\agents.py → D:\Projects & Stuff\multi-agent-research-team\src\research_team\config.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.12
Nodes (23): from_env(), get_config(), _parse_float(), _parse_int(), _parse_optional_int(), Runtime configuration and lazy factories for the LLM and web-search tool.  Desig, Build configuration from environment variables (and optional ``.env``)., Return the process-wide default configuration built from the environment. (+15 more)

### Community 1 - "Community 1"
Cohesion: 0.18
Nodes (15): build_parser(), _get_console(), _print_error(), _render_report(), _resolve_log_level(), run(), _save_report(), configure_logging() (+7 more)

### Community 2 - "Community 2"
Cohesion: 0.19
Nodes (16): coding_agent(), _common_kwargs(), manager_agent(), Agent factory functions.  Each factory returns a configured CrewAI :class:`~crew, Operational settings shared by every agent., The web researcher: gathers accurate, up-to-date source material., The engineer: turns research into practical, runnable examples., The synthesizer: reviews prior work and writes the final report. (+8 more)

### Community 3 - "Community 3"
Cohesion: 0.26
Nodes (16): Command-line interface.  The CLI is a thin adapter over :func:`research_team.cre, Parse ``argv`` and execute the workflow; return a process exit code., Parse ``argv`` and execute the workflow; return a process exit code., Entry point that also handles top-level, cross-cutting failures., Entry point that also handles top-level, cross-cutting failures., Structured output of a single research run.      Returning a structured object (, Total tokens consumed by the run, if reported by the provider., ResearchResult (+8 more)

### Community 4 - "Community 4"
Cohesion: 0.18
Nodes (11): AppConfig, Immutable, validated application configuration.      Instances are typically cre, base_config(), clean_env(), Shared pytest fixtures.  Tests are written to run *without* network access or re, A minimal, valid configuration suitable for unit tests., Remove all recognized environment variables for deterministic parsing., __getattr__() (+3 more)

### Community 5 - "Community 5"
Cohesion: 0.25
Nodes (12): main(), _fake_result(), Tests for the command-line interface (argument parsing, exit codes, wiring)., test_cli_overrides_reach_config(), test_config_error_returns_config_exit_code(), test_happy_path_returns_zero(), test_help_exits_zero(), test_missing_topic_errors() (+4 more)

### Community 6 - "Community 6"
Cohesion: 0.2
Nodes (12): coding_task(), manager_task(), Task factory functions.  Tasks describe *what* each agent must produce and *how*, Task A — web research producing a structured, sourced brief., Task B — practical code/analysis grounded in the research., Task C — the manager synthesizes everything into the final deliverable., research_task(), _bare_agent() (+4 more)

### Community 7 - "Community 7"
Cohesion: 0.25
Nodes (6): patch_litellm_cache_breakpoint(), Compatibility shims for third-party libraries.  This module isolates narrowly-sc, Stop CrewAI leaking its ``cache_breakpoint`` marker to LiteLLM providers.      C, Tests for third-party compatibility shims., test_shim_is_idempotent(), test_shim_strips_cache_breakpoint_marker()

### Community 8 - "Community 8"
Cohesion: 0.25
Nodes (7): _extract_token_usage(), Best-effort extraction of token-usage metrics from a ``CrewOutput``., _FakeOutput, _FakeUsage, test_extract_report_prefers_raw(), test_extract_token_usage_from_model_dump(), test_extract_token_usage_none()

### Community 9 - "Community 9"
Cohesion: 0.25
Nodes (6): _apply_runtime_defaults(), _rate_limit_error_type(), Workflow orchestration.  This module wires the agents and tasks into a determini, Apply privacy- and noise-friendly defaults for a standalone deployment.      Cre, Return the LiteLLM exception classes that are safe to retry.      Resolved lazil, _transient_error_types()

### Community 10 - "Community 10"
Cohesion: 0.36
Nodes (7): Execute ``action`` with exponential backoff on transient provider errors.      T, _run_with_retries(), Tests for workflow orchestration: retries, result extraction, error mapping.  Th, test_rate_limit_translated(), test_retry_exhausted_raises_workflow_error(), test_retry_succeeds_after_transient(), test_unexpected_error_wrapped()

### Community 11 - "Community 11"
Cohesion: 0.29
Nodes (7): _extract_report(), Normalize a CrewAI ``CrewOutput`` (or any result) to report text., Run the full research workflow and return a :class:`ResearchResult`.      Parame, run_research_workflow(), test_empty_topic_raises_value_error(), test_extract_report_empty_raises(), test_run_workflow_happy_path()

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (1): Task A: Web research.

### Community 13 - "Community 13"
Cohesion: 1.0
Nodes (1): Task B: Coding/analysis based on the research.

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (1): Task C: Manager synthesizes everything into a final deliverable.

## Knowledge Gaps
- **23 isolated node(s):** `Compatibility shims for third-party libraries.  This module isolates narrowly-sc`, `Stop CrewAI leaking its ``cache_breakpoint`` marker to LiteLLM providers.      C`, `Build configuration from environment variables (and optional ``.env``).`, `Typed exception hierarchy for the Multi-Agent Research Team.  Using a small, wel`, `Base class for all errors raised by this package.` (+18 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 12`** (1 nodes): `Task A: Web research.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 13`** (1 nodes): `Task B: Coding/analysis based on the research.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (1 nodes): `Task C: Manager synthesizes everything into a final deliverable.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppConfig` connect `Community 4` to `Community 0`, `Community 2`, `Community 3`, `Community 6`, `Community 8`, `Community 9`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.299) - this node is a cross-community bridge._
- **Why does `ResearchResult` connect `Community 3` to `Community 4`, `Community 5`, `Community 8`, `Community 9`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Why does `build_crew()` connect `Community 2` to `Community 9`, `Community 11`, `Community 6`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `AppConfig` (e.g. with `Agent factory functions.  Each factory returns a configured CrewAI :class:`~crew` and `Operational settings shared by every agent.`) actually correct?**
  _`AppConfig` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `WorkflowError` (e.g. with `Command-line interface.  The CLI is a thin adapter over :func:`research_team.cre` and `Parse ``argv`` and execute the workflow; return a process exit code.`) actually correct?**
  _`WorkflowError` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `RateLimitExceededError` (e.g. with `Command-line interface.  The CLI is a thin adapter over :func:`research_team.cre` and `Parse ``argv`` and execute the workflow; return a process exit code.`) actually correct?**
  _`RateLimitExceededError` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `ConfigError` (e.g. with `Command-line interface.  The CLI is a thin adapter over :func:`research_team.cre` and `Parse ``argv`` and execute the workflow; return a process exit code.`) actually correct?**
  _`ConfigError` has 18 INFERRED edges - model-reasoned connections that need verification._