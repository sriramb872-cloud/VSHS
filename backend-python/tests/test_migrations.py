"""Migration tests against a real MySQL server.

Gated on ``MIGRATION_TEST_DATABASE_URL`` pointing at a **disposable** database.
When the variable is unset, every test here skips, keeping the default
SQLite-backed suite fast and dependency-free. CI sets it and runs against a
MySQL 8.4 service container.

Covered:

* (a) fresh database + ``alembic upgrade head`` creates exactly the schema the
  SQLAlchemy models define (plus ``alembic_version``), stamped with the head
* (b) upgrade -> downgrade -> upgrade cycle is stable
* (c) a legacy ``schemadeploy.sql`` import upgrades **in place**: existing rows
  survive, the auth columns (``token_version``/``locked_until``/
  ``must_change_password``) and the ``refresh_tokens`` table appear
* (d) ``alembic check`` reports zero drift between models and migrations

The subprocess helper must override ``DATABASE_URL``: the test process has it
pinned to SQLite by ``conftest.py`` before any import happens.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCHEMADEPLOY_SQL = BACKEND_ROOT.parent / "schemadeploy.sql"
MIGRATION_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not MIGRATION_URL,
    reason="MIGRATION_TEST_DATABASE_URL not set (needs a disposable MySQL database)",
)

WINDOWS_MYSQL_CLI = Path(r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alembic(*args: str) -> subprocess.CompletedProcess:
    """Run alembic in a subprocess against the migration database.

    ``python -c ... argv[1:]`` avoids depending on console-script resolution
    and lets us inject the environment cleanly.
    """
    env = dict(os.environ)
    env["DATABASE_URL"] = MIGRATION_URL
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from alembic.config import main; main(argv=sys.argv[1:])",
            *args,
        ],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )


def _alembic_ok(*args: str) -> subprocess.CompletedProcess:
    proc = _alembic(*args)
    if proc.returncode != 0:
        pytest.fail(
            f"alembic {' '.join(args)} failed (rc={proc.returncode})\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )
    return proc


def _head() -> str:
    proc = _alembic_ok("heads")
    # Output format: "0002 (head)" — take the revision id of each line.
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    heads = [ln.split()[0] for ln in lines]
    assert len(heads) == 1, f"expected exactly one head, got {heads!r}"
    return heads[0]


def _reset(engine) -> None:
    """Drop every table so each test starts from a truly empty database."""
    with engine.begin() as conn:
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        for (table_name,) in conn.exec_driver_sql("SHOW TABLES").fetchall():
            conn.exec_driver_sql(f"DROP TABLE IF EXISTS `{table_name}`")
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")


def _tables(engine) -> set[str]:
    with engine.connect() as conn:
        return {row[0] for row in conn.exec_driver_sql("SHOW TABLES").fetchall()}


def _version(engine) -> str | None:
    with engine.connect() as conn:
        return conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()


def _import_schemadeploy(engine) -> None:
    """Import the legacy dump with the mysql CLI (no CREATE DATABASE/USE in it,
    so it loads straight into the database given on the command line)."""
    cli = shutil.which("mysql") or (
        str(WINDOWS_MYSQL_CLI) if WINDOWS_MYSQL_CLI.exists() else None
    )
    if cli is None:
        pytest.skip("mysql CLI client not found (required to import schemadeploy.sql)")
    if not SCHEMADEPLOY_SQL.exists():
        pytest.skip(f"{SCHEMADEPLOY_SQL} not present")

    url = make_url(MIGRATION_URL)
    proc = subprocess.run(
        [
            cli,
            f"--host={url.host}",
            f"--port={url.port or 3306}",
            f"--user={url.username}",
            f"--password={url.password or ''}",
            url.database,
        ],
        input=SCHEMADEPLOY_SQL.read_bytes(),
        capture_output=True,
        timeout=600,
    )
    if proc.returncode != 0:
        pytest.fail(
            "schemadeploy.sql import failed: "
            + proc.stderr.decode("utf-8", errors="replace")[:2000]
        )


def _insert_marker_row(engine) -> str:
    """Insert a marker into ``schools`` regardless of the legacy column set.

    Uses information_schema to satisfy every NOT NULL column that has no
    default, so the insert keeps working as the legacy schema evolves.
    """
    marker = "MIGRATION_MARKER"
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name, column_type, is_nullable, column_default, extra "
                "FROM information_schema.columns "
                "WHERE table_schema = DATABASE() AND table_name = 'schools' "
                "ORDER BY ordinal_position"
            )
        ).fetchall()
        assert rows, "legacy import produced no schools table"

        assignments = {}
        for name, col_type, nullable, default, extra in rows:
            if extra and "auto_increment" in (extra or ""):
                continue
            if nullable == "YES" or default is not None:
                continue
            if any(col_type.startswith(t) for t in ("int", "bigint", "tinyint", "smallint", "decimal", "float", "double")):
                assignments[name] = 1
            elif col_type.startswith(("date", "datetime", "timestamp")):
                assignments[name] = "2025-01-01" if col_type.startswith("date") and not col_type.startswith("datetime") else "2025-01-01 00:00:00"
            elif col_type.startswith("time"):
                assignments[name] = "00:00:00"
            else:
                assignments[name] = marker
        assert assignments, "no insertable NOT NULL columns found on schools"

        cols = ", ".join(f"`{c}`" for c in assignments)
        placeholders = ", ".join(f":{c}" for c in assignments)
        conn.execute(
            text(f"INSERT INTO schools ({cols}) VALUES ({placeholders})"),
            assignments,
        )
    return marker


@pytest.fixture()
def migration_engine():
    """Fresh, empty migration database for one test."""
    engine = create_engine(MIGRATION_URL)
    _reset(engine)
    try:
        yield engine
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# (a) Fresh database
# ---------------------------------------------------------------------------


def test_fresh_upgrade_creates_exactly_the_model_schema(migration_engine):
    from app.core.database import Base
    import app.models  # noqa: F401  (registers every model)

    _alembic_ok("upgrade", "head")

    actual = _tables(migration_engine)
    expected = set(Base.metadata.tables) | {"alembic_version"}
    assert actual == expected, (
        f"missing tables: {sorted(expected - actual)}; "
        f"unexpected tables: {sorted(actual - expected)}"
    )
    assert _version(migration_engine) == _head()


# ---------------------------------------------------------------------------
# (b) Upgrade -> downgrade -> upgrade cycle
# ---------------------------------------------------------------------------


def test_upgrade_downgrade_upgrade_cycle(migration_engine):
    from app.core.database import Base
    import app.models  # noqa: F401

    _alembic_ok("upgrade", "head")
    _alembic_ok("downgrade", "base")
    _alembic_ok("upgrade", "head")

    actual = _tables(migration_engine)
    expected = set(Base.metadata.tables) | {"alembic_version"}
    assert actual == expected, (
        f"after cycle - missing: {sorted(expected - actual)}; "
        f"unexpected: {sorted(actual - expected)}"
    )
    assert _version(migration_engine) == _head()


# ---------------------------------------------------------------------------
# (c) Legacy schemadeploy.sql upgrade preserves data
# ---------------------------------------------------------------------------


def test_legacy_import_upgrades_in_place_preserving_data(migration_engine):
    _import_schemadeploy(migration_engine)

    # The legacy database must NOT contain the auth additions yet.
    legacy_tables = _tables(migration_engine)
    assert "refresh_tokens" not in legacy_tables
    with migration_engine.connect() as conn:
        legacy_columns = {
            r[0]
            for r in conn.exec_driver_sql(
                "SHOW COLUMNS FROM users"
            ).fetchall()
        }
    assert "token_version" not in legacy_columns

    marker = _insert_marker_row(migration_engine)
    with migration_engine.connect() as conn:
        legacy_user_count = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM users"
        ).scalar()

    # The actual upgrade under test.
    _alembic_ok("upgrade", "head")

    # 1. Marker row survived.
    with migration_engine.connect() as conn:
        surviving = conn.exec_driver_sql("SELECT * FROM schools").fetchall()
    assert surviving, "schools rows disappeared during upgrade"
    assert any(
        marker in {str(v) for v in row} for row in surviving
    ), "marker school row was lost during upgrade"

    # 2. Legacy user data survived.
    with migration_engine.connect() as conn:
        upgraded_user_count = conn.exec_driver_sql("SELECT COUNT(*) FROM users").scalar()
    assert upgraded_user_count == legacy_user_count

    # 3. Auth additions exist now.
    with migration_engine.connect() as conn:
        upgraded_columns = {
            r[0] for r in conn.exec_driver_sql("SHOW COLUMNS FROM users").fetchall()
        }
    assert {"token_version", "locked_until", "must_change_password"} <= upgraded_columns
    assert "refresh_tokens" in _tables(migration_engine)

    # 4. Database is stamped at head.
    assert _version(migration_engine) == _head()


# ---------------------------------------------------------------------------
# (d) No model/migration drift
# ---------------------------------------------------------------------------


def test_alembic_check_reports_no_drift(migration_engine):
    _alembic_ok("upgrade", "head")
    proc = _alembic("check")
    assert proc.returncode == 0, (
        "alembic detected drift between models and migrations "
        "(create a new frozen revision instead of editing old ones):\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )
