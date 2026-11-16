"""Pure-ASGI middleware: request IDs, security headers, body limits, rate limits.

Written as raw ASGI (not ``BaseHTTPMiddleware``) so that streaming responses
(Server-Sent Events) pass through untouched and without buffering.
"""

from __future__ import annotations

import contextvars
import json
import re
import secrets
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from .ratelimit import SlidingWindowLimiter, client_ip, hash_client

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

#: The current request's ID, available to log records and error handlers.
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

_APP_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
    "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)
# Swagger UI / ReDoc are served from a CDN by FastAPI.
_DOCS_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; "
    "object-src 'none'; frame-ancestors 'none'"
)


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers") or []:
        if key == name:
            return bytes(value).decode("latin-1")
    return None


async def _send_json_error(
    send: Send,
    status: int,
    code: str,
    message: str,
    request_id: str,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
    retry_after: int | None = None,
) -> None:
    body = json.dumps(
        {
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "retry_after_seconds": retry_after,
            }
        }
    ).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
        (b"x-request-id", request_id.encode()),
    ]
    if retry_after is not None:
        headers.append((b"retry-after", str(retry_after).encode()))
    headers += extra_headers or []
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class SecurityMiddleware:
    """Adds request IDs and security headers; enforces body size and API rate limits."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_body_bytes: int,
        limiter: SlidingWindowLimiter,
        trusted_proxy_hops: int,
        ip_salt: str,
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.limiter = limiter
        self.trusted_proxy_hops = trusted_proxy_hops
        self.ip_salt = ip_salt

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = _header(scope, b"x-request-id")
        request_id = (
            incoming if incoming and _SAFE_REQUEST_ID.match(incoming) else secrets.token_hex(8)
        )
        token = request_id_var.set(request_id)
        scope.setdefault("state", {})["request_id"] = request_id
        path: str = scope.get("path", "")
        is_https = scope.get("scheme") == "https" or _header(scope, b"x-forwarded-proto") == "https"

        try:
            # --- request body size limit ------------------------------------
            length = _header(scope, b"content-length")
            if length and length.isdigit() and int(length) > self.max_body_bytes:
                await _send_json_error(
                    send, 413, "payload_too_large", "The request body is too large.", request_id
                )
                return

            # --- per-IP API rate limit (health checks are exempt) -----------
            if path.startswith("/api/") and not path.startswith("/api/health"):
                ip = client_ip(
                    _peer(scope), _header(scope, b"x-forwarded-for"), self.trusted_proxy_hops
                )
                allowed, retry_after = self.limiter.hit(hash_client(ip, self.ip_salt))
                if not allowed:
                    await _send_json_error(
                        send,
                        429,
                        "too_many_requests",
                        "Too many requests. Please slow down.",
                        request_id,
                        retry_after=retry_after,
                    )
                    return

            received = 0

            async def limited_receive() -> Message:
                nonlocal received
                message = await receive()
                if message["type"] == "http.request":
                    received += len(message.get("body", b""))
                    if received > self.max_body_bytes:
                        raise _BodyTooLarge()
                return message

            async def send_with_headers(message: Message) -> None:
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers") or [])
                    headers += _security_headers(path, request_id, is_https)
                    message["headers"] = headers
                await send(message)

            try:
                await self.app(scope, limited_receive, send_with_headers)
            except _BodyTooLarge:
                await _send_json_error(
                    send, 413, "payload_too_large", "The request body is too large.", request_id
                )
        finally:
            request_id_var.reset(token)


class _BodyTooLarge(Exception):
    pass


def _peer(scope: Scope) -> str | None:
    client = scope.get("client")
    return client[0] if client else None


def _security_headers(path: str, request_id: str, is_https: bool) -> list[tuple[bytes, bytes]]:
    csp = _DOCS_CSP if path.startswith(("/api/docs", "/api/redoc")) else _APP_CSP
    headers = [
        (b"x-request-id", request_id.encode()),
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), interest-cohort=()"),
        (b"cross-origin-opener-policy", b"same-origin"),
        (b"content-security-policy", csp.encode()),
    ]
    if is_https:
        headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))
    return headers
