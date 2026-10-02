# backend-python/main.py
"""SCHOLARIS API entry point.

IMPORTANT: this module performs NO database schema changes. Historically it
ran ``Base.metadata.create_all`` plus ALTER TABLE reconciliation at import
time, which raced between gunicorn workers (see gunicorn_conf.py -> several
workers, each importing this module). Schema management now lives exclusively
in Alembic (``alembic upgrade head``), executed exactly once by the deploy
start command BEFORE any worker starts. See docs/MIGRATIONS.md.
"""
import fnmatch
import json
import logging
import os
import time
import traceback
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

import app.models  # Ensure all models are registered in Base.metadata
from app.core.rate_limit import limiter

from app.routers.v1 import (
    auth,
    dashboard,
    homework,
    exam,
    marks,
    report_card,
    timetable,
    announcement,
    notification,
    calendar_event,
    settings,
    academic_years,
    schools,
    grades,
    sections,
    subjects,
    teachers,
    students,
    principals,
    users,
    attendance,
    student_enrollments,
    grade_subjects,
    teacher_subjects,
    teacher_assignments,
    audit_logs,
    files,
    search,
    slip_tests,
    roles,
    reports,
    subscriptions,
    subscription_plans,
)

logger = logging.getLogger("scholaris")


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------
# Every line carries timestamp + level + logger + message, and request lines
# additionally carry request_id/method/path/status/duration. NEVER log
# passwords, access tokens, refresh tokens, reset tokens or DB credentials -
# only the fields below are attached.

class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class TextLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = []
        for key in ("request_id", "method", "path", "status", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                extras.append(f"{key}={value}")
        return f"{base} {' '.join(extras)}" if extras else base


def configure_logging() -> None:
    handler = logging.StreamHandler()
    log_format = os.getenv("LOG_FORMAT", "json").strip().lower()
    if log_format == "text":
        handler.setFormatter(
            TextLogFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    else:
        handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())


configure_logging()


# ---------------------------------------------------------------------------
# CORS - configurable via environment, never a wildcard
# ---------------------------------------------------------------------------
# ALLOWED_ORIGINS          comma-separated exact origins (overrides defaults)
# ALLOWED_ORIGIN_PATTERNS  comma-separated fnmatch patterns, opt-in only -
#                          e.g. https://*.vercel.app for preview deployments.
DEFAULT_ALLOWED_ORIGINS = [
    "https://vshs.vercel.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "https://scholaris.in",
    "https://www.scholaris.in",
]


def _split_csv(raw: str) -> list:
    return [item.strip() for item in raw.split(",") if item.strip()]


_configured_origins = _split_csv(os.getenv("ALLOWED_ORIGINS", ""))
ALLOWED_ORIGINS = _configured_origins or list(DEFAULT_ALLOWED_ORIGINS)
ALLOWED_ORIGIN_PATTERNS = _split_csv(os.getenv("ALLOWED_ORIGIN_PATTERNS", ""))


def origin_allowed(origin: str) -> bool:
    if origin in ALLOWED_ORIGINS:
        return True
    return any(
        fnmatch.fnmatchcase(origin, pattern)
        for pattern in ALLOWED_ORIGIN_PATTERNS
    )


def origin_patterns_to_regex(patterns: list) -> str | None:
    """Combine fnmatch-style patterns into a single regex for Starlette's
    CORSMiddleware (``allow_origin_regex``, matched with ``fullmatch``).

    Starlette >= 1.0 removed the ``allow_origin_patterns`` keyword, so the
    opt-in pattern list must be compiled here. ``fnmatch.translate`` anchors
    each pattern at the end; the explicit group keeps alternation correct.
    """
    if not patterns:
        return None
    return "|".join(f"(?:{fnmatch.translate(pattern)})" for pattern in patterns)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SCHOLARIS School ERP API",
    description="Production-ready multi-school ERP backend for SCHOLARIS V1",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration (exact origins only; credentials are allowed because the
# list is explicit - never "*").
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=origin_patterns_to_regex(ALLOWED_ORIGIN_PATTERNS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attach a correlation id to every request and emit one structured
    access-log line per request (method, path, status, duration, request id).

    Tokens/passwords are never read here and bodies are never logged.
    Unhandled exceptions are logged with their traceback by the global
    exception handler below (same request state, so the request id matches).
    """
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log every unhandled exception with its full traceback and still
    return a CORS-friendly response.

    Without this handler, an unhandled exception is caught by Starlette's
    ServerErrorMiddleware, which sits OUTSIDE the CORSMiddleware added
    above. That means the 500 response it returns never passes back
    through CORSMiddleware, so no Access-Control-Allow-Origin header is
    attached - the browser then reports a CORS error even though CORS is
    configured correctly. The real bug is always the underlying 500; this
    handler makes that 500 visible in the logs (check `railway logs`) and
    keeps the response CORS-compliant so the browser shows the real error
    instead of a misleading CORS message.
    """
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        "Unhandled exception on %s %s:\n%s",
        request.method,
        request.url.path,
        traceback.format_exc(),
        extra={"request_id": request_id, "method": request.method, "path": request.url.path},
    )

    origin = request.headers.get("origin")
    headers = {}
    if origin and origin_allowed(origin):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    if request_id:
        headers["X-Request-ID"] = request_id

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers,
    )


# Static and Media Files
media_path = os.path.join(os.path.dirname(__file__), "media")
os.makedirs(media_path, exist_ok=True)

app.mount("/media", StaticFiles(directory=media_path), name="media")


# Root Endpoints
@app.get("/", tags=["Root"])
async def root():
    return {
        "app": "SCHOLARIS School ERP API",
        "version": "1.0.0",
        "status": "active"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Liveness probe: the process is up and serving requests.

    Deliberately touches NO dependencies - a failed database must not make
    the orchestrator kill/restart otherwise-healthy workers in a loop.
    Use /ready to know whether the app can actually serve traffic.
    """
    return {"status": "ok"}


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness probe: the app AND its database are reachable.

    Returns 200 when the database answers a trivial query, 503 otherwise.
    Never exposes connection strings, hostnames or other internals.
    """
    from sqlalchemy import text
    from app.core.database import engine

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - any driver error means "not ready"
        logger.warning("readiness check failed: database unreachable")
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "checks": {"database": "failed"}},
        )
    return {"status": "ready", "checks": {"database": "ok"}}


# Register API Routers under /api/v1 prefix
PREFIX = "/api/v1"

app.include_router(auth.router, prefix=PREFIX)
app.include_router(dashboard.router, prefix=PREFIX)
app.include_router(homework.router, prefix=PREFIX)
app.include_router(exam.router, prefix=PREFIX)
app.include_router(marks.router, prefix=PREFIX)
app.include_router(report_card.router, prefix=PREFIX)
app.include_router(timetable.router, prefix=PREFIX)
app.include_router(announcement.router, prefix=PREFIX)
app.include_router(notification.router, prefix=PREFIX)
app.include_router(calendar_event.router, prefix=PREFIX)
app.include_router(settings.router, prefix=PREFIX)
app.include_router(academic_years.router, prefix=PREFIX)
app.include_router(schools.router, prefix=PREFIX)
app.include_router(grades.router, prefix=PREFIX)
app.include_router(sections.router, prefix=PREFIX)
app.include_router(subjects.router, prefix=PREFIX)
app.include_router(teachers.router, prefix=PREFIX)
app.include_router(students.router, prefix=PREFIX)
app.include_router(principals.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(attendance.router, prefix=PREFIX)
app.include_router(student_enrollments.router, prefix=PREFIX)
app.include_router(grade_subjects.router, prefix=PREFIX)
app.include_router(teacher_subjects.router, prefix=PREFIX)
app.include_router(teacher_assignments.router, prefix=PREFIX)
app.include_router(audit_logs.router, prefix=PREFIX)
app.include_router(files.router, prefix=PREFIX)
app.include_router(search.router, prefix=PREFIX)
app.include_router(roles.router, prefix=PREFIX)
app.include_router(reports.router, prefix=PREFIX)
app.include_router(slip_tests.router, prefix=PREFIX)
app.include_router(subscriptions.router, prefix=PREFIX)
app.include_router(subscription_plans.router, prefix=PREFIX)
