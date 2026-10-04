# backend-python/alembic/env.py
"""Alembic environment for SCHOLARIS.

* Reads the DATABASE_URL environment variable (the same variable the app
  uses, including a local backend-python/.env via python-dotenv).
* Uses the live SQLAlchemy models as the metadata target for autogenerate.
* Supports both offline (`alembic upgrade head --sql`) and online modes.

The application secret (SECRET_KEY) is required only because importing the
models pulls in `app.core.config`, which validates both variables at import.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make backend-python/ importable regardless of the invocation directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()  # local development .env (never overrides existing env vars)

config = context.config

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is required to run migrations"
    )
if database_url.startswith("mysql://"):
    database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)

config.set_main_option("sqlalchemy.url", database_url)

# Configure alembic's own logging; application log lines emitted by
# legacy-repair steps go through the root logger.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.core.database import Base  # noqa: E402
import app.models  # noqa: E402,F401  - registers every model in Base.metadata

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DB connection)."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# One MySQL advisory lock serialises migrations across processes. Without it,
# two deploys starting together (Railway overlap, a restart-on-failure loop, a
# manual redeploy during an auto-deploy) run DDL at the same time and MySQL
# fails with error 1684 "skipped since its definition is being modified by
# concurrent DDL statement". With it, the second process simply waits, then
# finds everything already applied (every revision is idempotent) and moves on.
MIGRATION_LOCK_NAME = "scholaris_alembic_migrations"
MIGRATION_LOCK_WAIT_SECONDS = 180


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        use_lock = connection.dialect.name == "mysql"
        if use_lock:
            acquired = connection.exec_driver_sql(
                "SELECT GET_LOCK(%s, %s)",
                (MIGRATION_LOCK_NAME, MIGRATION_LOCK_WAIT_SECONDS),
            ).scalar()
            # GET_LOCK is session-scoped, so committing does NOT release it;
            # the commit only closes SQLAlchemy's auto-begun transaction so
            # Alembic can manage its own.
            connection.commit()
            if acquired != 1:
                raise RuntimeError(
                    "Could not acquire the migration lock within "
                    f"{MIGRATION_LOCK_WAIT_SECONDS}s - another migration is "
                    "still running."
                )
        try:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()
        finally:
            if use_lock:
                connection.exec_driver_sql(
                    "SELECT RELEASE_LOCK(%s)", (MIGRATION_LOCK_NAME,)
                )
                connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()