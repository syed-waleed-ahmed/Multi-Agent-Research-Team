# Free-Tier Infrastructure

This project is designed so that **every required component has a genuinely
free option with no credit card**. Free does not mean unlimited: every hosted
provider below enforces quotas, and the app is built around them (per-IP and
global job limits, a bounded queue, result caching, per-call retries, provider
fallbacks).

> **Verification date: 2026-11-15.** Limits change without notice. Each entry
> says *how* it was verified. "Measured" means read from live API responses
> with a real free account; "official docs" means read on the provider's own
> page that day; "third-party" means not confirmed on an official page.
> Re-check before relying on any number.

## 1. Summary

| Component | Choice | Category | Card required | Required? |
| --- | --- | --- | --- | --- |
| Web hosting (API + website) | Render Free web service | Free hosted service | Not stated for Free instances (see notes) | Yes (or any Docker host) |
| Database | SQLite (bundled) or Neon Free Postgres | OSS / free hosted service | No | SQLite: yes · Neon: optional |
| LLM | Groq free tier | Free API quota | No | Yes (or another provider) |
| Web search | Serper free credits | Free API quota | No | Yes (or Tavily) |
| Fallback search | Tavily free plan | Free API quota | No | Optional |
| Fallback LLMs | Gemini, OpenRouter, Ollama, OpenAI-compatible | Free quota / self-hosted | No | Optional |
| CI | GitHub Actions | Free for public repositories | No | Yes |
| Application stack | CrewAI, LiteLLM, FastAPI, React … | Free open-source software | — | Yes |

Nothing in the default configuration can start billing you: there is no paid
add-on, no metered integration, and no trial presented as permanent.

## 2. Free hosted services

### Render — Free web service (selected host)

Source: <https://render.com/docs/free> (official docs, read 2026-11-15).

| Item | Free-tier behaviour |
| --- | --- |
| Service | One Docker web service serving the website **and** the API |
| Spin-down | After **15 minutes** without inbound traffic; the next request wakes it (**about one minute**) |
| Instance hours | **750 Free instance hours per workspace per calendar month**; when exhausted, Free services are suspended until next month (enough for one always-on service) |
| Filesystem | **Ephemeral** — local SQLite data is lost on redeploy, restart or spin-down; persistent disks are not available on Free |
| Restarts | "Render might restart a Free web service at any time" |
| Shutdown window | On deploys the old instance keeps serving for 60 s, then gets SIGTERM and is killed 30 s later. `maxShutdownDelaySeconds` is rejected on Free ("max shutdown delay is not supported for free tier services", observed 2026-11-16), so the app's graceful shutdown is sized to fit 30 s |
| Bandwidth | Counts against the workspace's monthly included bandwidth; **if no payment method is on file, Render suspends Free services instead of billing** |
| RAM / CPU | Not stated on that page. Widely reported as 512 MB RAM / 0.1 CPU (third-party). The app measured ~310 MB RSS with the full agent stack loaded, so the default is **one concurrent job** |
| Credit card | The Free docs do not state that a card is required for Free instances |
| Free Postgres | Render's own Free Postgres **expires 30 days after creation** (deleted after a 14-day grace period) — therefore **not used**; Neon is recommended instead |

How the app adapts: health checks at `/api/health`; jobs persisted before
execution and recovered after restarts; the UI shows an honest "waking up the
server" state during cold starts and warns when storage is ephemeral.

### Neon — Free Postgres (optional, recommended for persistence)

Source: Neon FAQ "free plan limits and quotas" (official, last updated
2026-10-01; read via search results on 2026-11-15).

| Item | Free plan |
| --- | --- |
| Price | $0/month, **no credit card**, Neon does **not bill overages** on Free |
| Storage | 1 GB per project |
| Compute | 100 CU-hours per project per month; scales to zero after 5 minutes idle |
| Fit | The app stores small rows (jobs, events, reports ≤ 60 KB); 1 GB holds many thousands of reports, and expired jobs are deleted after `JOB_RETENTION_DAYS` (default 7) |

Connect with `DATABASE_URL=postgresql://…?sslmode=require`; the app routes it to
the BSD-licensed `pg8000` driver with verified TLS.

### GitHub Actions — CI

Standard GitHub-hosted runners are free for public repositories. The CI
pipeline needs **no secrets**: tests use scripted model responses and a
deterministic fake engine.

### Evaluated and rejected

| Option | Why not |
| --- | --- |
| Hugging Face Spaces (Docker) | Official docs (2026-11-15): "Gradio and Docker Spaces run on compute and require a paid plan to create" (PRO). Only Static Spaces and ZeroGPU Gradio Spaces remain free. |
| Render Free Postgres | Expires after 30 days, then deleted. |
| Cerebras Inference (as a default) | Official rate-limits page: free access is a time-limited **trial**, not an ongoing free tier. |
| Vercel Hobby / Cloudflare Pages | Not needed: one container serves the static site. They remain an option for split hosting (`VITE_API_BASE_URL` + `CORS_ORIGINS`); note Vercel Hobby is limited to non-commercial use. |

## 3. Free API quotas (user-provided credentials)

### Groq — default LLM

Verified by **measurement** on 2026-11-15 (models list endpoint and
`x-ratelimit-*` response headers of a free account):

| Model (served by Groq in 2026-11) | Requests/day | Tokens/minute |
| --- | --- | --- |
| `openai/gpt-oss-120b` (default) | 1,000 | 8,000 |
| `openai/gpt-oss-20b` | 1,000 | 8,000 |
| `qwen/qwen3.8-27b` | 1,000 | 8,000 |

* Limits are **per model**; your organisation's exact values are at
  <https://console.groq.com/settings/limits>.
* Groq **retired its Llama 3.x chat models** in 2026 (`llama-3.3-70b-versatile`
  now returns `model_not_found`). The readiness check verifies the configured
  model is still served.
* 8,000 tokens/minute is the binding constraint. A measured research run uses
  ~10–12K tokens and ~7 model requests, so runs regularly hit HTTP 429; the
  engine retries **only the failed request** with backoff + jitter, honouring
  `Retry-After`.

### Serper — default web search

Third-party sources (several, consistent): **2,500 free queries at signup, no
credit card**; sources disagree on whether the credit is one-time or expires.
The official pricing page was not readable signed-out. Each run makes 2–6
searches (`quick` 2, `standard` 4, `deep` 6), i.e. roughly 400–1,200 runs per
free allowance. Readiness checks never probe Serper, because each request
costs a credit.

### Tavily — optional fallback search

Official docs (2026-11-15): **1,000 free API credits per month, no credit
card**; basic search costs 1 credit; credits reset on the 1st of each month.
When both keys are set, the engine tries Serper first and falls back to Tavily
(`SEARCH_PROVIDERS` controls the order).

### Optional fallback LLMs

| Provider | Status (2026-11-15) | Notes |
| --- | --- | --- |
| Google Gemini (AI Studio) | Free tier for Flash models; per-model limits are **no longer published** on Google's rate-limits page — check your AI Studio quota page | Free-tier terms allow Google to use submitted content to improve its products; do not send sensitive data |
| OpenRouter `:free` models | Free models with daily request limits; exact numbers **not verified** | Configure `OPENROUTER_MODEL` with a `:free` model id |
| Ollama / OpenAI-compatible | Self-hosted, free | Runs on your own hardware; no quota |

Fallbacks are tried, per stage, only when the current provider stays
rate-limited or unavailable after retries (`LLM_FALLBACK_PROVIDERS`).

## 4. Free open-source software

| Layer | Packages (license) |
| --- | --- |
| Agents & LLM access | CrewAI (MIT), LiteLLM (MIT) |
| API & server | FastAPI (MIT), Starlette (BSD-3), Uvicorn (BSD-3), Pydantic (MIT) |
| Persistence | SQLAlchemy (MIT), Alembic (MIT), pg8000 (BSD-3), SQLite (public domain) |
| HTTP & CLI | httpx (BSD-3), Rich (MIT), python-dotenv (BSD-3) |
| Frontend (shipped) | React 19, react-router 8, react-markdown 10, remark-gfm, rehype-highlight (MIT; highlight.js BSD-3), lucide-react (ISC), Inter font via @fontsource (OFL-1.1) |
| Frontend (build/test only) | Vite 8, Tailwind CSS 4, TypeScript 6 (Apache-2.0), ESLint 10, Vitest 5, Playwright (Apache-2.0) — exact pins in `frontend/package.json` |
| Tooling | pytest (MIT), Ruff (MIT), mypy (MIT), Playwright (Apache-2.0), Vitest (MIT), ESLint (MIT) |

The psycopg drivers (LGPL) were deliberately avoided in favour of `pg8000`.
CrewAI pulls in further transitive dependencies (for example `chromadb`); see
`SECURITY.md` for how their advisories are handled.

## 5. Realistic capacity of the free deployment

Measured on 2026-11-15 (real Groq + Serper, one instance):

| Depth | Wall time | Tokens | Searches |
| --- | --- | --- | --- |
| quick | ~13–18 s | ~10K | 2 |
| standard | ~28 s (incl. rate-limit backoff) | ~12K | 2–4 |

| Bottleneck | Approximate ceiling |
| --- | --- |
| Groq tokens/minute (8K) | ~1 run per 1–2 minutes sustained |
| Groq requests/day (1,000 per model) | ~140 runs/day theoretical |
| Serper credits (2,500) | ~400–1,200 runs in total |
| Render Free RAM | 1 concurrent run (configurable) |

The shipped Render blueprint therefore sets `GLOBAL_JOBS_PER_DAY=60`,
`JOBS_PER_IP_PER_DAY=10`, `MAX_CONCURRENT_JOBS=1` and `MAX_QUEUED_JOBS=5`.
This is a **portfolio-scale demo**, not a high-traffic service.

**Upgrade path (all optional):** a paid Groq tier or another LiteLLM provider
(raise TPM), a larger instance (raise `MAX_CONCURRENT_JOBS`), a managed
Postgres plan, or a separate worker process. No code changes are required for
any of these.
