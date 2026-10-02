"""Pytest configuration.

IMPORTANT: environment variables are set BEFORE the application modules are
imported, because ``app.core.config`` reads them at import time and
``app.core.database`` creates the engine. Tests always run against a fresh,
isolated SQLite database file — never against the configured MySQL server.
"""

from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

# --- Make the backend package importable no matter where pytest runs from ---
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# --- Environment must be prepared before any app import --------------------
_TEST_DB_PATH = os.path.join(tempfile.mkdtemp(prefix="scholaris_test_"), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ.setdefault(
    "SECRET_KEY",
    "test-secret-key-not-used-in-production-0123456789",
)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ["ALLOWED_ORIGINS"] = "https://example.com,http://localhost:5173"
# Opt-in pattern support must also work end-to-end (Starlette >= 1.0 needs a
# compiled regex; see main.origin_patterns_to_regex).
os.environ["ALLOWED_ORIGIN_PATTERNS"] = "https://*.preview.example.com"
# Rate limiting is exercised separately; keep the suite fast and stable.
os.environ["RATE_LIMIT_ENABLED"] = "false"
# Deterministic token lifetimes regardless of a developer's local .env.
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "14")
os.environ.setdefault("LOGIN_MAX_FAILED_ATTEMPTS", "10")
os.environ.setdefault("LOGIN_LOCKOUT_MINUTES", "15")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401  (registers every model on Base.metadata)
import app.api.deps as deps  # noqa: E402
from app.core.database import Base  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    """Session-scoped test engine (file-based SQLite, single shared connection).

    ``StaticPool`` keeps one connection for the whole session, so data flushed
    by a test's session is immediately visible to the app's request sessions.
    """
    eng = create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_connection, _record):  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


@pytest.fixture(scope="session", autouse=True)
def _create_schema(engine):
    import app.core.database as database_module

    # ``/ready`` uses ``app.core.database.engine`` directly (function-local
    # import). Point it at the single-connection test engine so the probe is
    # thread-safe and never touches a real database.
    database_module.engine = engine
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def db(engine) -> Iterator[Session]:
    """Per-test database session.

    Test data is committed (routers use their own sessions), so the fixture
    wipes every table *before* each test instead of rolling back afterwards.
    """
    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    _wipe_all(engine)
    session: Session = TestingSession()
    try:
        yield session
    finally:
        session.close()


def _wipe_all(engine) -> None:
    """Delete every row from every table (children first)."""
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """HTTP client wired to the test database session."""

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    # Routers import ``get_db`` from ``app.api.deps`` — override that exact
    # function object (``app.core.database.get_db`` is dead code for routes).
    app.dependency_overrides[deps.get_db] = _override_get_db
    try:
        yield TestClient(app, raise_server_exceptions=True)
    finally:
        app.dependency_overrides.pop(deps.get_db, None)


@pytest.fixture
def world(db: Session):
    """Two complete, independent schools (A and B) plus a platform super-admin.

    Every tenant-scoped domain exists in both schools, so cross-tenant tests
    can be exhaustive (see ``tests/world.py``).
    """
    from types import SimpleNamespace

    from tests.factories import make_user
    from tests.world import build_school

    a = build_school(db, "A")
    b = build_school(db, "B")
    superadmin = make_user(db, None, role="SUPER_ADMIN", display_name="Platform Admin")
    return SimpleNamespace(a=a, b=b, superadmin=superadmin)
