"""Alembic environment.

Used both programmatically (``Database.migrate`` passes an open connection via
``config.attributes["connection"]``) and from the ``alembic`` CLI, where the
database URL comes from ``DATABASE_URL`` (see ``alembic.ini`` at the repo root).
"""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine

from research_team.web.db import normalize_database_url
from research_team.web.models import Base

config = context.config
target_metadata = Base.metadata


def _run(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    url, connect_args = normalize_database_url(
        os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url") or ""
    )
    engine = create_engine(url, connect_args=connect_args)
    with engine.begin() as conn:
        _run(conn)


def run_migrations_offline() -> None:
    url, _ = normalize_database_url(
        os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url") or ""
    )
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
