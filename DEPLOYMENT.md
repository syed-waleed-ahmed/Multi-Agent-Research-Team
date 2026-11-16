# Deployment

The application ships as **one Docker image** that serves both the website and
its API. The reference deployment is **Render Free** (web service) with an
optional **Neon Free** Postgres database. See
[FREE_TIER_INFRASTRUCTURE.md](FREE_TIER_INFRASTRUCTURE.md) for the verified
limits of each provider.

```text
 Browser ──HTTPS──▶ Render Free web service (Docker)
                    ├─ React website (static files)
                    ├─ FastAPI  /api/...  (+ SSE progress stream)
                    └─ job runner (thread pool) ──▶ Groq (LLM), Serper/Tavily (search)
                                   │
                                   └──▶ DATABASE_URL: Neon Postgres (persistent)
                                        or SQLite on the container disk (ephemeral)
```

## What you need (all free, no credit card)

| Account | Used for | Get it at |
| --- | --- | --- |
| GitHub | Source + CI | <https://github.com> |
| Render | Hosting | <https://render.com> (sign in with GitHub) |
| Groq | LLM API key | <https://console.groq.com/keys> |
| Serper | Search API key | <https://serper.dev> |
| Neon *(optional, recommended)* | Persistent Postgres | <https://neon.tech> |
| Tavily *(optional)* | Fallback search | <https://tavily.com> |

## 1. Deploy to Render (Blueprint)

The repository contains [`render.yaml`](render.yaml), which defines one Free
Docker web service with conservative limits.

1. Push this repository to GitHub (the `main` branch).
2. In Render: **New → Blueprint**, select the repository, confirm `render.yaml`.
3. When prompted, enter the secret values:
   * `GROQ_API_KEY`, `SERPER_API_KEY` (required)
   * `DATABASE_URL` (optional — see step 2 below; leave empty to use ephemeral SQLite)
   * `TAVILY_API_KEY` (optional)
4. Apply. Render builds the image (several minutes on the first build: the
   frontend is compiled and CrewAI's dependencies are installed) and starts the
   service. Health check path: `/api/health`.
5. Your site is live at `https://<service-name>.onrender.com`.

`IP_HASH_SALT` is generated automatically. Change limits later under
**Environment** in the Render dashboard; see `.env.example` for every option.

## 2. Add persistent storage with Neon (recommended)

Without it, results live in SQLite on Render's ephemeral disk and disappear
whenever the instance restarts or spins down (the website warns users about
this and encourages downloads).

1. Create a free Neon project; copy the **connection string** (it looks like
   `postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`).
2. Set it as `DATABASE_URL` on the Render service and redeploy.
3. Tables are created automatically at startup (Alembic migrations).
   `GET /api/health/ready` then reports `database: postgresql (persistent)`.

## 3. Verify the deployment

Run these against your URL (replace `$APP`):

```bash
APP=https://your-service.onrender.com
curl -s $APP/api/health                 # {"status":"ok","version":"2.0.0"}
curl -s $APP/api/health/ready | jq      # database, configuration, job_runner, llm, search
curl -s $APP/api/v1/meta | jq .models   # models offered to visitors
```

Then in a browser:

1. Open the site; the landing page loads (first visit after idle may take ~1 minute).
2. Start a research run with depth **quick**; watch the three agents progress.
3. Open the report, the sources, and the citation check; download Markdown.
4. Check the browser console for errors.
5. Try a second identical request: it is served instantly from the result cache.

`/api/health/ready` returning `"degraded"` means a non-critical check failed —
most often that the configured `GROQ_MODEL` is not served by Groq any more.

### Client IP behind Render's proxy

Per-visitor quotas need the real client IP. Render runs behind Cloudflare, and
on the live deployment the last `X-Forwarded-For` hop was an internal Render
proxy address that **changed between requests** (so quotas keyed on it did not
work), while the left-most entry is whatever the client sent. The blueprint
therefore sets `CLIENT_IP_HEADERS=CF-Connecting-IP` — a header Cloudflare
overwrites on every request — with `TRUSTED_PROXY_HOPS=1` only as a fallback.
`True-Client-IP` is deliberately not trusted: Cloudflare only sets it when a
zone enables it, and otherwise a client could supply its own.

**Verify after deploying:** start one run, then `GET $APP/api/v1/usage` a few
times; `jobs_today` must stay at 1. Sending a forged `CF-Connecting-IP` header
must not change the count (Cloudflare replaces it). On other hosts, configure
only headers your own edge proxy guarantees to overwrite.

## 4. Run the container anywhere (local or another host)

```bash
docker build -t multi-agent-research-team .
docker run --rm -p 8000:8000 --env-file .env multi-agent-research-team
# open http://localhost:8000
```

Mount a volume for durable SQLite: `-v "$PWD/data:/app/data"`.

## 5. Run without Docker (development)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[web]"
cp .env.example .env                                 # add your keys
(cd frontend && npm ci && npm run build)             # build the website
research-team-web                                    # http://localhost:8000
```

For frontend development with hot reload, run `research-team-web` and, in a
second terminal, `cd frontend && npm run dev` (Vite proxies `/api` to port 8000).

## 6. Split hosting (optional)

To serve the static site from a CDN (e.g. Cloudflare Pages) while the API stays
on Render:

1. Build the frontend with `VITE_API_BASE_URL=https://your-service.onrender.com`.
2. Set `CORS_ORIGINS=https://your-site.pages.dev` on the API (explicit origins only;
   `*` is rejected).
3. If the static host sends its own Content-Security-Policy, add the API origin
   to `connect-src` (the app's default policy only allows same-origin requests).

This removes the cold-start delay for the landing page, but the first research
request still waits for the API to wake up.

## 7. Operating notes

* **Graceful shutdown.** On redeploy, running jobs are stopped and recorded as
  `interrupted`; queued jobs resume when the new instance starts (persistent
  database required for them to survive).
* **Retention.** Finished jobs are deleted after `JOB_RETENTION_DAYS` (default 7).
* **Logs.** Structured application logs go to stderr (visible in Render's
  log stream). Client IPs are never logged or stored — only salted hashes.
* **Model retirement.** If Groq retires the configured model, readiness turns
  `degraded` and runs fail with `provider_unavailable`; set `GROQ_MODEL` to a
  current model (see `GET /api/v1/meta` and the Groq console).
* **Costs.** None by default. Render suspends (rather than bills) Free services
  that exceed their allowance when no payment method is on file.

## Deployment status of this repository

The deployment configuration (`Dockerfile`, `render.yaml`) is complete, and CI
builds and smoke-tests the Docker image. A public deployment requires the
repository owner's Render account and API keys, so **no live URL is claimed
here**; add it to the README once you have deployed and verified it.
