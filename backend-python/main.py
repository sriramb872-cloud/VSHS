# backend-python/main.py
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.core.database import Base, engine
import app.models  # Ensure all models are registered in Base.metadata

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
)

logger = logging.getLogger("scholaris")

Base.metadata.create_all(bind=engine)

ALLOWED_ORIGINS = [
    "https://vshs.vercel.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "https://scholaris.in",
    "https://www.scholaris.in",
]


def _column_ddl(column) -> str:
    """Render the DDL fragment for a single ORM column."""
    return column.type.compile(engine.dialect)


def _quote(identifier: str) -> str:
    return f"`{identifier}`"


def _reconcile_enum_column(connection, table, column, live_column: dict) -> None:
    """Widen a MySQL ENUM column when the model declares new values.

    Only ever *adds* values: the emitted ENUM keeps every value already
    present in the database and appends the ones the ORM declares but the
    column is missing, in the model's declared order. Rows that already hold a
    value are untouched, and no value is ever removed.
    """
    column_type = column.type
    declared = list(getattr(column_type, "enums", None) or [])
    if not declared or column_type.__class__.__name__ != "Enum":
        return
    if engine.dialect.name != "mysql":
        return

    live_type = live_column.get("type")
    live_values = list(getattr(live_type, "enums", None) or [])
    if not live_values:
        return

    missing = [value for value in declared if value not in live_values]
    if not missing:
        return

    merged = live_values + missing
    rendered = ", ".join(f"'{value}'" for value in merged)
    nullability = "" if column.nullable else " NOT NULL"
    connection.execute(
        text(
            f"ALTER TABLE {_quote(table.name)} "
            f"MODIFY COLUMN {_quote(column.name)} "
            f"ENUM({rendered}){nullability}"
        )
    )
    logger.info(
        "Startup schema migration: widened enum %s.%s with %s",
        table.name,
        column.name,
        ", ".join(missing),
    )


def apply_startup_schema_migrations() -> None:
    """Apply small, idempotent upgrades required by the current ORM models.

    ``create_all`` creates missing *tables* but it never adds columns to
    tables that already exist. Any installation whose database predates a
    column that was later added to a model therefore boots fine and then
    fails at query time with MySQL error 1054 "Unknown column ... in 'field
    list'". That is what broke ``GET /dashboard/principal`` for principals:
    ``attendance_records.remarks`` was declared on the ORM model but absent
    from the database, so any query selecting ``Attendance`` raised a 500.

    Rather than special-casing one column at a time, this reconciles *every*
    table in ``Base.metadata`` and adds any column the models declare but the
    database is missing. The migration is strictly additive: it never drops
    or renames anything, so it cannot destroy existing data.

    IMPORTANT: gunicorn boots multiple worker processes (see
    gunicorn_conf.py -> workers = 4), and each worker imports this module
    independently. That means this function can run concurrently in several
    workers against the same database. Without the try/except below, two
    workers can both see the column missing and both issue
    ``ALTER TABLE ... ADD COLUMN``; the loser gets a "Duplicate column name"
    error, which is an unhandled exception at import time and crashes that
    worker on boot. We treat "column already exists" as success instead of
    letting it propagate.
    """
    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            present_tables = set(inspector.get_table_names())
            for table in Base.metadata.sorted_tables:
                if table.name not in present_tables:
                    # create_all already handled missing tables.
                    continue
                live_columns = {c["name"]: c for c in inspector.get_columns(table.name)}
                for column in table.columns:
                    if column.name not in live_columns:
                        nullability = "" if column.nullable else " NOT NULL"
                        connection.execute(
                            text(
                                f"ALTER TABLE {_quote(table.name)} "
                                f"ADD COLUMN {_quote(column.name)} "
                                f"{_column_ddl(column)}{nullability}"
                            )
                        )
                        logger.info(
                            "Startup schema migration: added %s.%s",
                            table.name,
                            column.name,
                        )
                        continue

                    # MySQL ENUM columns can also drift: adding a value to the
                    # model's Enum() does not alter an existing column, so the
                    # database keeps the old value list and any INSERT/UPDATE
                    # using the new value fails with errno 1265 "Data truncated
                    # for column". That is what broke POST /attendance/{id}/void
                    # when "VOID" was added to the Attendance model.
                    _reconcile_enum_column(
                        connection, table, column, live_columns[column.name]
                    )
    except (OperationalError, ProgrammingError) as exc:
        # Another worker already added the column (or is adding it right
        # now) - this is expected under concurrent startup and is not fatal.
        logger.warning(
            "Startup schema migration skipped "
            "(likely already applied by another worker): %s", exc
        )


apply_startup_schema_migrations()

app = FastAPI(
    title="SCHOLARIS School ERP API",
    description="Production-ready multi-school ERP backend for SCHOLARIS V1",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

from app.core.rate_limit import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    logger.error(
        "Unhandled exception on %s %s:\n%s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )

    origin = request.headers.get("origin")
    headers = {}
    if origin in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=headers,
    )


@app.get("/debug/cors")
def debug_cors():
    return {
        "message": "THIS IS THE DEPLOYED BACKEND",
        "cors_origins": ALLOWED_ORIGINS,
    }

# Static and Media Files
import os
from fastapi.staticfiles import StaticFiles

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
    return {"status": "ok"}

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