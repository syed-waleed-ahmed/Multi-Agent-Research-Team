"""Client identification and in-memory rate limiting.

Two layers protect the shared free-tier quotas:

1. **Per-request limits** (this module): a sliding-window limiter caps API
   requests per client IP per minute, and a counter caps concurrent
   Server-Sent-Event streams. These are in-memory, which is correct for the
   supported single-instance deployment.
2. **Job quotas** (see ``routes.py``): per-IP hourly/daily and global daily
   limits on *research jobs*, counted from the database so they survive
   restarts when a persistent database is configured.

Client IPs are never stored: they are reduced to a salted SHA-256 digest.
"""

from __future__ import annotations

import hashlib
import math
import threading
import time
from collections import deque
from collections.abc import Mapping


def client_ip(peer: str | None, forwarded_for: str | None, trusted_hops: int) -> str:
    """Resolve the real client IP.

    ``X-Forwarded-For`` is only honoured when ``trusted_hops`` > 0 (i.e. the
    operator declared how many reverse proxies sit in front of the app). The
    entry appended by the outermost trusted proxy is used, so a client cannot
    spoof its address by sending its own header.
    """
    if trusted_hops > 0 and forwarded_for:
        chain = [part.strip() for part in forwarded_for.split(",") if part.strip()]
        if len(chain) >= trusted_hops:
            return chain[-trusted_hops]
    return peer or "unknown"


def hash_client(ip: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()


class SlidingWindowLimiter:
    """Thread-safe sliding-window counter keyed by client."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._last_prune = time.monotonic()

    def hit(self, key: str, now: float | None = None) -> tuple[bool, int]:
        """Record a request. Returns ``(allowed, retry_after_seconds)``."""
        now = time.monotonic() if now is None else now
        with self._lock:
            if now - self._last_prune > self.window:
                self._prune(now)
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = max(1, math.ceil(hits[0] + self.window - now))
                return False, retry_after
            hits.append(now)
            return True, 0

    def _prune(self, now: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - self.window]:
            del self._hits[key]
        self._last_prune = now


class ConcurrencyLimiter:
    """Caps simultaneous long-lived connections (SSE streams) per client."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def acquire(self, key: str) -> bool:
        with self._lock:
            current = self._counts.get(key, 0)
            if current >= self.limit:
                return False
            self._counts[key] = current + 1
            return True

    def release(self, key: str) -> None:
        with self._lock:
            current = self._counts.get(key, 0) - 1
            if current <= 0:
                self._counts.pop(key, None)
            else:
                self._counts[key] = current

    def snapshot(self) -> Mapping[str, int]:
        with self._lock:
            return dict(self._counts)
