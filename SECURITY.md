# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 2.0.x | Yes |
| 1.0.x | Security fixes until 2027-05-15 |
| < 1.0 | No |

## Reporting a vulnerability

Please do not open a public issue for security vulnerabilities.

Report suspected vulnerabilities privately using one of the following:

- GitHub's private vulnerability reporting: open the repository's **Security**
  tab and choose **Report a vulnerability**.
- Email the maintainer at **syedwaleedahmed9@gmail.com** with a description of
  the issue, steps to reproduce, and any relevant logs (with secrets redacted).

You can expect an acknowledgement within a few business days. Once the issue is
confirmed, a fix will be prepared and released, and the report will be credited
unless you prefer to remain anonymous.

## Threat model (public web deployment)

The web app accepts anonymous input and spends a shared, limited budget of
free API quota. The main risks and their controls:

| Threat | Controls |
| --- | --- |
| **Quota exhaustion / abuse** — one visitor burns the free LLM or search quota | Per-IP hourly and daily job limits and a global daily limit (counted in the database); bounded queue (`MAX_QUEUED_JOBS`) and concurrency (`MAX_CONCURRENT_JOBS`); per-IP API request rate limit; per-IP cap on concurrent event streams; per-run search budget (2–6 searches) and per-agent iteration caps; result cache and request de-duplication so repeats cost nothing; wall-clock timeout per job. The API is **not** a general LLM proxy: it only runs the fixed research workflow. |
| **Prompt injection** via the topic or web pages | User input is sanitised (control characters and tag-like delimiters removed) and embedded in delimited blocks explicitly framed as data; search results are truncated and wrapped in an "untrusted data" envelope; agents have **no code execution, file, or browsing tools** — only the fixed search tool — so a successful injection can at worst degrade a report. |
| **SSRF** | The server only calls fixed, hard-coded provider endpoints (Groq/LiteLLM, Serper, Tavily, configured fallbacks). It never fetches URLs supplied by users or found in search results; HTTP redirects are not followed. Provider base URLs come only from operator configuration. |
| **XSS / malicious links** in AI output | The frontend renders Markdown without raw HTML; links are restricted to `http(s)`, open with `rel="noopener noreferrer nofollow"`; strict Content-Security-Policy (`script-src 'self'`, `connect-src 'self'`, `frame-ancestors 'none'`); `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, HSTS over HTTPS. |
| **Fabricated or unverifiable citations** | Every link in a report is checked against the URLs the search tool actually returned; unmatched links are flagged in the UI and the methodology. Sources are labelled "retrieved by web search", never "verified". |
| **Unauthorised job control** | Job ids are 128-bit random values (capability URLs). Cancelling requires an owner token returned once at creation; only its SHA-256 hash is stored and it is compared in constant time. |
| **Information leakage** | Errors use a stable envelope with user-safe messages; stack traces and provider payloads are only logged server-side. Credentials are never sent to the browser, logged, or included in `repr()` output. |
| **Privacy** | Client IPs are never stored or logged — only salted SHA-256 hashes (`IP_HASH_SALT`). CrewAI telemetry and tracing are disabled by default. Finished jobs are deleted after `JOB_RETENTION_DAYS`. |
| **Oversized requests** | `MAX_REQUEST_BYTES` body limit (checked on `Content-Length` and while streaming), field length limits, and a maximum report size. |
| **CORS** | Same-origin by default; cross-origin access only for explicitly listed `CORS_ORIGINS` (wildcards are rejected). |
| **Client IP spoofing** | The client IP comes from headers a trusted edge overwrites (`CLIENT_IP_HEADERS`, e.g. Cloudflare's `CF-Connecting-IP` on Render), validated as IP addresses; otherwise from `X-Forwarded-For` only when `TRUSTED_PROXY_HOPS` is set, using the entry appended by the outermost trusted proxy — never the client-controlled left-most entry. |
| **Container hardening** | The image runs as a non-root user, contains no secrets (`.dockerignore` excludes `.env`), and needs no runtime downloads. |

## Handling secrets

The application requires API credentials (`GROQ_API_KEY`, `SERPER_API_KEY`, and
optionally others such as `TAVILY_API_KEY` or `DATABASE_URL`). To keep them safe:

- Store credentials only in a local `.env` file or your host's secret store
  (e.g. Render environment variables). `.env` is git-ignored and must never be
  committed; commit only `.env.example`, which contains placeholders.
- Never paste real keys into issues, pull requests, logs, or screenshots.
- Rotate any key that may have been exposed. Groq keys can be rotated at
  <https://console.groq.com/keys> and Serper keys at <https://serper.dev/api-key>.
- Keys are passed explicitly to each provider client and are not copied into
  the process environment.

## Dependency advisories

CI runs `pip-audit` and `npm audit` on every push. Fixable advisories in
transitive Python dependencies are addressed with security floors in
[`constraints/security.txt`](constraints/security.txt), applied by the Docker
image and the CI audit.

**Reviewed exceptions (2026-11-15):**

| Package | Advisories | Why accepted | Revisit |
| --- | --- | --- | --- |
| `chromadb` 1.5.9 (via CrewAI) | PYSEC-2026-311, PYSEC-2026-3813, PYSEC-2026-3814, PYSEC-2026-3815 | All concern the **Chroma server** (authentication/RBAC, pre-auth code injection). No fixed release exists yet. This app never starts or exposes a Chroma server and does not enable CrewAI memory or knowledge features. | When a fixed `chromadb` is released, or if CrewAI memory is ever enabled |

**Python 3.10 note.** The fixed releases of `pillow` (13.0), `soupsieve` (4.0)
and `filelock` (4.2.1) require Python ≥ 3.11, so a Python 3.10 install keeps
older versions. The application does not use the affected code paths (image
decoding, CSS selectors, soft file locks), but **deploy on Python 3.11+**
(the Docker image uses 3.12).
