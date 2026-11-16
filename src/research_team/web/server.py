"""``research-team-web`` — run the web application with Uvicorn.

Reads ``HOST`` (default ``0.0.0.0``), ``PORT`` (default ``8000``; Render and
most PaaS hosts set it), ``FORWARDED_ALLOW_IPS`` (proxies trusted for
``X-Forwarded-Proto``; default ``127.0.0.1``), ``LOG_LEVEL`` and
``GRACEFUL_SHUTDOWN_SECONDS`` (how long open connections, such as live
progress streams, may stay open after SIGTERM before the app's own job drain
runs; default 5 — browsers reconnect event streams automatically).
"""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    uvicorn.run(
        "research_team.web.app:create_app",
        factory=True,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        proxy_headers=True,
        forwarded_allow_ips=os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"),
        timeout_graceful_shutdown=int(os.getenv("GRACEFUL_SHUTDOWN_SECONDS", "5")),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=os.getenv("ACCESS_LOG", "true").lower() in {"1", "true", "yes"},
        server_header=False,
    )


if __name__ == "__main__":
    main()
