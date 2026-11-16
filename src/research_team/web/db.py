"""Database engine, sessions, and migrations.

Supported backends
------------------
* **SQLite** (default): zero setup, ideal locally. On free hosts with an
  ephemeral filesystem (e.g. Render Free) data is lost on restart — the app
  reports this through ``GET /api/v1/meta`` (``persistence: "ephemeral"``).
* **PostgreSQL** (recommended in production): e.g. a free Neon database. URLs
  like ``postgres://`` or ``postgresql://`` are routed to the pure-Python,
  BSD-licensed ``pg8000`` driver; ``sslmode=require`` is translated into a
  verified TLS context.

Migrations are managed by Alembic and applied automatically at startup.
"""

from __future__ import annotations

import ssl
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..logging_config import get_logger

log = get_logger("web.db")

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

_SSL_MODES_REQUIRING_TLS = {"require", "verify-ca", "verify-full"}
_PG_ONLY_PARAMS = {"sslmode", "channel_binding", "sslrootcert"}


def normalize_database_url(url: str) -> tuple[str, dict[str, Any]]:
    """Return a SQLAlchemy URL plus driver ``connect_args``."""
    url = url.strip()
    connect_args: dict[str, Any] = {}
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+pg8000://" + url[len("postgresql://") :]
    if url.startswith("postgresql+pg8000://"):
        parts = urlsplit(url)
        params = dict(parse_qsl(parts.query))
        sslmode = params.get("sslmode", "").lower()
        query = urlencode({k: v for k, v in params.items() if k not in _PG_ONLY_PARAMS})
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
        if sslmode in _SSL_MODES_REQUIRING_TLS:
            connect_args["ssl_context"] = ssl.create_default_context()
    return url, connect_args


class Database:
    """Owns the SQLAlchemy engine and session factory."""

    def __init__(self, url: str) -> None:
        self.url, connect_args = normalize_database_url(url)
        self.dialect = self.url.split(":", 1)[0].split("+", 1)[0]
        engine_kwargs: dict[str, Any] = {"pool_pre_ping": True, "future": True}
        #: In-memory SQLite shares ONE connection across threads (StaticPool);
        #: sqlite3 connections are not safe for concurrent use, so access to an
        #: in-memory database is serialised. File/Postgres databases use a
        #: normal per-thread connection pool and need no lock.
        self._memory_lock: threading.RLock | None = None

        if self.dialect == "sqlite":
            connect_args.update({"check_same_thread": False, "timeout": 15})
            if self.url in {"sqlite://", "sqlite:///:memory:"}:
                engine_kwargs["poolclass"] = StaticPool  # one shared in-memory DB
                self._memory_lock = threading.RLock()
            else:
                self._ensure_sqlite_dir(self.url)
        else:
            engine_kwargs.update({"pool_size": 5, "max_overflow": 5, "pool_recycle": 300})

        self.engine: Engine = create_engine(self.url, connect_args=connect_args, **engine_kwargs)
        if self.dialect == "sqlite":
            event.listen(self.engine, "connect", _sqlite_pragmas)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    @staticmethod
    def _ensure_sqlite_dir(url: str) -> None:
        path = url.split("sqlite:///", 1)[-1]
        if path and path != ":memory:":
            Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    @property
    def persistence(self) -> str:
        """'ephemeral' for SQLite (assume container disk), 'persistent' otherwise."""
        return "ephemeral" if self.dialect == "sqlite" else "persistent"

    @contextmanager
    def _serialised(self) -> Iterator[None]:
        if self._memory_lock is None:
            yield
            return
        with self._memory_lock:
            yield

    @contextmanager
    def session(self) -> Iterator[Session]:
        """A transactional session: commits on success, rolls back on error."""
        with self._serialised():
            session = self._sessions()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    def ping(self) -> bool:
        try:
            with self._serialised(), self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as exc:  # pragma: no cover - exercised via readiness tests
            log.warning("Database ping failed: %s", exc)
            return False

    def migrate(self) -> None:
        """Apply all pending Alembic migrations."""
        from alembic import command
        from alembic.config import Config

        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS_DIR).replace("%", "%%"))
        with self._serialised(), self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        log.info("Database migrations applied (%s)", self.dialect)

    def dispose(self) -> None:
        self.engine.dispose()


def _sqlite_pragmas(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
    finally:
        cursor.close()
