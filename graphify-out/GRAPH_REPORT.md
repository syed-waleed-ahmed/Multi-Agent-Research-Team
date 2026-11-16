# Graph Report - D:\Projects & Stuff\multi-agent-research-team  (2026-11-16)

## Corpus Check
- 128 files · ~95,196 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 927 nodes · 2807 edges · 82 communities detected
- Extraction: 40% EXTRACTED · 60% INFERRED · 0% AMBIGUOUS · INFERRED: 1698 edges (avg confidence: 0.6)
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
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]

## God Nodes (most connected - your core abstractions)
1. `AppConfig` - 126 edges
2. `ConfigError` - 96 edges
3. `RateLimitExceededError` - 95 edges
4. `RunControl` - 81 edges
5. `WorkflowError` - 68 edges
6. `ProgressEvent` - 63 edges
7. `EventType` - 61 edges
8. `ProviderUnavailableError` - 54 edges
9. `get()` - 51 edges
10. `Stage` - 49 edges

## Surprising Connections (you probably didn't know these)
- `total_tokens()` --calls--> `get()`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\research_team\crew.py → D:\Projects & Stuff\multi-agent-research-team\frontend\e2e\failures.spec.ts
- `Agent factory functions.  Each factory returns a configured CrewAI :class:`~crew` --uses--> `AppConfig`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\research_team\agents.py → D:\Projects & Stuff\multi-agent-research-team\src\research_team\config.py
- `Operational settings shared by every agent.` --uses--> `AppConfig`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\research_team\agents.py → D:\Projects & Stuff\multi-agent-research-team\src\research_team\config.py
- `The web researcher: gathers accurate, up-to-date, sourced material.` --uses--> `AppConfig`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\research_team\agents.py → D:\Projects & Stuff\multi-agent-research-team\src\research_team\config.py
- `The engineer: turns research into practical, runnable examples.` --uses--> `AppConfig`  [INFERRED]
  D:\Projects & Stuff\multi-agent-research-team\src\research_team\agents.py → D:\Projects & Stuff\multi-agent-research-team\src\research_team\config.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (136): Operational settings shared by every agent., The web researcher: gathers accurate, up-to-date source material., The engineer: turns research into practical, runnable examples., The synthesizer: reviews prior work and writes the final report., Command-line interface.  The CLI is a thin adapter over :func:`research_team.cre, Parse ``argv`` and execute the workflow; return a process exit code., Parse ``argv`` and execute the workflow; return a process exit code., Precedence: --log-level, then --verbose, then LOG_LEVEL, then INFO. (+128 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (73): jsonResponse(), create_app(), _error(), _load_engine_config(), _mount_frontend(), FastAPI application factory.  ``create_app()`` wires settings, the database, the, Serve the built single-page app, with history-API fallback to index.html., Build the ASGI application.      Parameters are injectable for tests and embeddi (+65 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (54): Initial schema: research jobs, results, and events.  Revision ID: 0001_initial R, upgrade(), Apply all pending Alembic migrations., _serialised(), session(), Exception, client_ip(), hash_client() (+46 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (49): coding_agent(), _common_kwargs(), manager_agent(), Agent factory functions.  Each factory returns a configured CrewAI :class:`~crew, Operational settings shared by every agent., The web researcher: gathers accurate, up-to-date, sourced material., The engineer: turns research into practical, runnable examples., The synthesizer: reviews prior work and writes the final report. (+41 more)

### Community 4 - "Community 4"
Cohesion: 0.12
Nodes (59): BaseModel, DeclarativeBase, Enum, ProviderHealth, Caches the result of a lightweight LLM-provider probe., Base, JobEvent, SQLAlchemy ORM models.  Three tables:  * ``research_jobs`` — one row per submitt (+51 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (32): ApiError, apiUrl(), errorFromResponse(), isAbortError(), isRecord(), parseErrorBody(), parseRetryAfterHeader(), request() (+24 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (50): normalize_database_url(), Return a SQLAlchemy URL plus driver ``connect_args``., Alembic environment.  Used both programmatically (``Database.migrate`` passes an, _run(), run_migrations_offline(), run_migrations_online(), get(), CheckResult (+42 more)

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (28): Return an error message if ``provider`` lacks required settings., provider_spec(), resolve_providers(), RunControl, test_non_groq_provider_does_not_require_groq_key(), test_cancel_raises_on_next_check(), test_check_passes_when_idle(), test_deadline_raises_timeout() (+20 more)

### Community 8 - "Community 8"
Cohesion: 0.1
Nodes (27): build_parser(), _ensure_utf8_streams(), _get_console(), main(), _print_error(), _render_report(), _resolve_log_level(), run() (+19 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (31): assemble_document(), build_methodology(), build_sources_section(), check_citations(), check_python_blocks(), enforce_max_length(), extract_urls(), normalize_citation_markers() (+23 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (23): build_web_search_tool(), Construct the web-search tool (Serper, falling back to Tavily) for ``config``., build_search_provider(), build_search_tool(), clean_text(), FallbackSearch, format_results_for_agent(), _HttpProvider (+15 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (22): configure_crewai_console(), patch_litellm_cache_breakpoint(), Compatibility shims for third-party libraries.  This module isolates narrowly-sc, Stop CrewAI leaking its ``cache_breakpoint`` marker to LiteLLM providers.      C, Align CrewAI's global console formatter with our ``verbose`` setting.      CrewA, run_research_workflow(), Tests for third-party compatibility shims., test_console_formatter_follows_verbose_flag() (+14 more)

### Community 12 - "Community 12"
Cohesion: 0.1
Nodes (11): createHistoryStore(), parseHistory(), sanitizeEntry(), MemoryStorage, isStorageAvailable(), safeGet(), safeRemove(), safeSet() (+3 more)

### Community 13 - "Community 13"
Cohesion: 0.23
Nodes (9): acceptSnapshot(), buildTimeline(), describe(), jobReducer(), mergeEvents(), num(), str(), withoutResult() (+1 more)

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (2): agentCard(), expectAllAgents()

### Community 15 - "Community 15"
Cohesion: 0.29
Nodes (3): cn(), navClass(), buttonClasses()

### Community 16 - "Community 16"
Cohesion: 0.33
Nodes (5): base_config(), clean_env(), Shared pytest fixtures.  Tests are written to run *without* network access or re, A minimal, valid configuration suitable for unit tests., Remove all recognized environment variables for deterministic parsing.

### Community 17 - "Community 17"
Cohesion: 0.5
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 0.5
Nodes (2): copyText(), onCopy()

### Community 19 - "Community 19"
Cohesion: 0.67
Nodes (0): 

### Community 20 - "Community 20"
Cohesion: 0.67
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 0.67
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 0.67
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 0.67
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 0.67
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (2): focusTab(), onKeyDown()

### Community 26 - "Community 26"
Cohesion: 0.67
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (0): 

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (0): 

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (0): 

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (0): 

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (0): 

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (0): 

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (0): 

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (0): 

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (0): 

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (0): 

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (0): 

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (0): 

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (0): 

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (0): 

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (0): 

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (0): 

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (0): 

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (0): 

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (0): 

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (0): 

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (0): 

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (0): 

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (0): 

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (0): 

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (0): 

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (0): 

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (0): 

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (0): 

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (1): ephemeral' for SQLite (assume container disk), 'persistent' otherwise.

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (1): A transactional session: commits on success, rolls back on error.

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Base class for all errors raised by this package.

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Raised when configuration is missing or invalid.      Typically caused by absent

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Raised when a required third-party dependency is not installed.

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): Raised when the research workflow fails to produce a result.

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): Task A — web research producing a structured, sourced brief.

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): Task B — practical code/analysis grounded in the research.

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (1): Task C — the manager synthesizes everything into the final deliverable.

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (1): Task A: Web research.

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (1): Task B: Coding/analysis based on the research.

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (1): Task C: Manager synthesizes everything into a final deliverable.

## Knowledge Gaps
- **67 isolated node(s):** `Compatibility shims for third-party libraries.  This module isolates narrowly-sc`, `Stop CrewAI leaking its ``cache_breakpoint`` marker to LiteLLM providers.      C`, `Align CrewAI's global console formatter with our ``verbose`` setting.      CrewA`, `Typed exception hierarchy for the Multi-Agent Research Team.  Using a small, wel`, `Base class for all errors raised by this package.` (+62 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 27`** (2 nodes): `GitHubMark.tsx`, `GitHubMark()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (2 nodes): `Layout.tsx`, `Layout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (2 nodes): `LogoMark.tsx`, `LogoMark()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (2 nodes): `PageFallback.tsx`, `PageFallback()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (2 nodes): `ThemeToggle.tsx`, `ThemeToggle()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (2 nodes): `cn()`, `ConnectionIndicator.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (2 nodes): `Alert()`, `Alert.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (2 nodes): `Badge()`, `Badge.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (2 nodes): `Button()`, `Button.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (2 nodes): `CodeSnippet()`, `CodeSnippet.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (2 nodes): `Skeleton.tsx`, `Skeleton()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (2 nodes): `Spinner.tsx`, `Spinner()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (2 nodes): `useHistory.ts`, `useHistory()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (2 nodes): `useJob.ts`, `useJob()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (2 nodes): `useNow.ts`, `useNow()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (2 nodes): `useUsage.ts`, `useUsage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (2 nodes): `ids.ts`, `newIdempotencyKey()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `eslint.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `vite.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `console.spec.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `journey.spec.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `mobile.spec.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `resilience.spec.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `screenshots.spec.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `App.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `main.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `vite-env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Footer.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `ActivityTimeline.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `AgentCard.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `HistoryList.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `JobHeader.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `JobStatusBadge.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `QuotaCard.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `CitationPanel.test.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `CitationPanel.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Markdown.test.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `SourcesList.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `format.test.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `NotFoundPage.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `RouteErrorPage.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `setup.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `ephemeral' for SQLite (assume container disk), 'persistent' otherwise.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `A transactional session: commits on success, rolls back on error.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Base class for all errors raised by this package.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `Raised when configuration is missing or invalid.      Typically caused by absent`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Raised when a required third-party dependency is not installed.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `Raised when the research workflow fails to produce a result.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `Task A — web research producing a structured, sourced brief.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `Task B — practical code/analysis grounded in the research.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `Task C — the manager synthesizes everything into the final deliverable.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `Task A: Web research.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `Task B: Coding/analysis based on the research.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `Task C: Manager synthesizes everything into a final deliverable.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get()` connect `Community 6` to `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 10`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Why does `AppConfig` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 11`, `Community 16`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Why does `ConfigError` connect `Community 0` to `Community 1`, `Community 10`, `Community 3`, `Community 7`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 120 inferred relationships involving `AppConfig` (e.g. with `Agent factory functions.  Each factory returns a configured CrewAI :class:`~crew` and `Operational settings shared by every agent.`) actually correct?**
  _`AppConfig` has 120 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `ConfigError` (e.g. with `Command-line interface.  The CLI is a thin adapter over :func:`research_team.cre` and `Precedence: --log-level, then --verbose, then LOG_LEVEL, then INFO.`) actually correct?**
  _`ConfigError` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 92 inferred relationships involving `RateLimitExceededError` (e.g. with `DepthProfile` and `ResearchOptions`) actually correct?**
  _`RateLimitExceededError` has 92 INFERRED edges - model-reasoned connections that need verification._
- **Are the 74 inferred relationships involving `RunControl` (e.g. with `DepthProfile` and `ResearchOptions`) actually correct?**
  _`RunControl` has 74 INFERRED edges - model-reasoned connections that need verification._