from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import cast

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from mood_tracker.config import get_settings
from mood_tracker.infrastructure.db.models import Base

config = context.config
arguments = context.get_x_argument(as_dictionary=True)
explicit_database_url = arguments.get("database_url")
expected_database = arguments.get("expected_database")

if explicit_database_url is None:
    if expected_database is not None:
        raise RuntimeError("expected_database requires an explicit database_url")
    database_url = get_settings().DB_URL
elif expected_database is None:
    raise RuntimeError("explicit database_url requires expected_database")
else:
    database_url = explicit_database_url

config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a database connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection, expected_database: str | None) -> None:
    """Configure and run migrations through an existing connection."""
    if expected_database is not None:
        actual_database = cast(
            str, connection.execute(text("SELECT current_database()")).scalar_one()
        )
        if actual_database != expected_database:
            raise RuntimeError(
                "Migration database does not match the expected test database: "
                f"expected {expected_database!r}, got {actual_database!r}"
            )
        # PostgreSQL starts a transaction even for the verification query.
        # Finish it so Alembic owns and commits the migration transaction.
        connection.commit()
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run all pending migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations, expected_database)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations with an async database connection."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
