# backend-python/app/core/academic_year_migrations.py
"""Startup reconciliation for the Academic Year system.

``main.py:apply_startup_schema_migrations`` only *adds missing columns* and
widens ENUMs. The Academic Year work needs a little more than that: two new
columns have to be backfilled from existing data, two unique constraints have
to be swapped, and the "at most one ACTIVE year per school" invariant has to
be repaired on databases that predate the lifecycle.

Everything in here is:

* **additive / non-destructive** -- no column, index or row is ever dropped
  unless it is immediately replaced by a stronger equivalent, and no value is
  overwritten with anything that cannot be derived from the data itself;
* **idempotent** -- every statement is guarded by an existence (or
  duplicate-content) check, so running it on every boot is free;
* **fail-soft** -- each step runs in its own try/except so a problem in one
  step never prevents the API from booting.
"""
import logging

from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError

logger = logging.getLogger("scholaris")

STATUS_UPCOMING = "UPCOMING"
STATUS_ACTIVE = "ACTIVE"
STATUS_CLOSED = "CLOSED"
STATUS_ARCHIVED = "ARCHIVED"


def _step(fn, label: str) -> None:
    """Run one migration step; log-and-continue on any failure."""
    try:
        fn()
    except ProgrammingError as exc:
        logger.warning(
            "Academic year migration step skipped (%s): %s", label, exc
        )
    except Exception as exc:  # noqa: BLE001 - boot must never be blocked
        logger.error("Academic year migration step failed (%s): %s", label, exc)


# --------------------------------------------------------------------------
# schema helpers
# --------------------------------------------------------------------------


def _column_names(connection, table: str) -> set:
    try:
        return {c["name"] for c in inspect(connection).get_columns(table)}
    except Exception:  # noqa: BLE001
        return set()


def _index_names(connection, table: str) -> set:
    try:
        inspector = inspect(connection)
        names = {i["name"] for i in inspector.get_indexes(table) if i.get("name")}
        names |= {c["name"] for c in inspector.get_unique_constraints(table) if c.get("name")}
        return names
    except Exception:  # noqa: BLE001
        return set()


def _ensure_column(connection, table: str, column: str, ddl: str) -> None:
    """Add a column when the live table does not have it yet."""
    if column in _column_names(connection, table):
        return
    connection.execute(text(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {ddl}"))
    logger.info("Startup schema migration: added %s.%s", table, column)


def _ensure_index(connection, table: str, name: str, columns) -> None:
    if name in _index_names(connection, table):
        return
    cols = ", ".join(f"`{c}`" for c in columns)
    connection.execute(text(f"CREATE INDEX `{name}` ON `{table}` ({cols})"))
    logger.info("Startup schema migration: created index %s on %s", name, table)


def _has_foreign_key(connection, table: str, column: str) -> bool:
    count = connection.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = :table_name AND COLUMN_NAME = :column_name "
            "AND REFERENCED_TABLE_NAME IS NOT NULL"
        ),
        {"table_name": table, "column_name": column},
    ).scalar()
    return bool(count)


def _ensure_foreign_key(connection, table: str, column: str, ref_table: str, ref_column: str) -> None:
    if _has_foreign_key(connection, table, column):
        return
    connection.execute(
        text(
            f"ALTER TABLE `{table}` ADD FOREIGN KEY (`{column}`) "
            f"REFERENCES `{ref_table}` (`{ref_column}`) ON DELETE SET NULL"
        )
    )
    logger.info(
        "Startup schema migration: added FK %s.%s -> %s.%s",
        table, column, ref_table, ref_column,
    )


def _drop_unique_if_exists(connection, table: str, name: str) -> None:
    if name not in _index_names(connection, table):
        return
    connection.execute(text(f"ALTER TABLE `{table}` DROP INDEX `{name}`"))
    logger.info("Startup schema migration: dropped index %s on %s", name, table)


def _duplicate_groups(connection, sql: str):
    """Return the first few groups that violate a prospective unique index."""
    try:
        return list(connection.execute(text(sql)).fetchall())
    except Exception:  # noqa: BLE001 - table may not exist yet
        return []


def _ensure_unique(connection, table: str, name: str, columns, duplicate_sql: str) -> None:
    """Add ``name UNIQUE (columns)`` if missing *and* the data allows it.

    ``duplicate_sql`` must return rows when the current data would violate the
    constraint. If it does, the constraint is deliberately NOT added: refusing
    to boot (or silently deleting data) would be far worse than reporting it.
    """
    if name in _index_names(connection, table):
        return
    dupes = _duplicate_groups(connection, duplicate_sql)
    if dupes:
        logger.error(
            "Academic year migration: NOT adding unique constraint %s on %s; "
            "existing conflicting rows: %s",
            name, table, dupes[:5],
        )
        return
    cols = ", ".join(f"`{c}`" for c in columns)
    connection.execute(text(f"ALTER TABLE `{table}` ADD CONSTRAINT `{name}` UNIQUE ({cols})"))
    logger.info(
        "Startup schema migration: added unique constraint %s on %s (%s)",
        name, table, cols,
    )


# --------------------------------------------------------------------------
# data steps
# --------------------------------------------------------------------------


def _backfill_status(connection) -> None:
    # 1. Blank status (column just added, or a raw insert) -> sensible default.
    connection.execute(
        text(
            "UPDATE academic_years SET status = :upcoming "
            "WHERE status IS NULL OR status = ''"
        ),
        {"upcoming": STATUS_UPCOMING},
    )
    # 2. `is_current` has always meant "this is the live year"; promote those.
    connection.execute(
        text(
            "UPDATE academic_years SET status = :active "
            "WHERE is_current = 1 AND status <> :active AND status <> :archived"
        ),
        {"active": STATUS_ACTIVE, "archived": STATUS_ARCHIVED},
    )
    # 3. Years that ended in the past and are not current are closed.
    connection.execute(
        text(
            "UPDATE academic_years SET status = :closed "
            "WHERE status IN (:upcoming, :active) "
            "AND end_date IS NOT NULL AND end_date < CURDATE() AND is_current = 0"
        ),
        {"closed": STATUS_CLOSED, "upcoming": STATUS_UPCOMING, "active": STATUS_ACTIVE},
    )
    logger.info("Startup schema migration: reconciled academic_years.status")


def _repair_single_active(connection) -> None:
    """Enforce at most one ACTIVE year per school.

    Keeps the year that contains today when there is one, otherwise the most
    recently ended ACTIVE year, and closes the rest. Only ``status`` /
    ``is_current`` are touched - no row is ever deleted.
    """
    rows = connection.execute(
        text(
            "SELECT academic_year_id, school_id FROM academic_years "
            "WHERE status = :active"
        ),
        {"active": STATUS_ACTIVE},
    ).fetchall()
    by_school: dict = {}
    for year_id, school_id in rows:
        by_school.setdefault(school_id, []).append(year_id)

    for school_id, year_ids in by_school.items():
        if len(year_ids) < 2:
            continue
        ids_sql = ", ".join(str(int(y)) for y in year_ids)
        keep = connection.execute(
            text(
                "SELECT academic_year_id FROM academic_years "
                f"WHERE academic_year_id IN ({ids_sql}) "
                "ORDER BY (start_date <= CURDATE() AND end_date >= CURDATE()) DESC, "
                "end_date DESC, start_date DESC, academic_year_id DESC "
                "LIMIT 1"
            )
        ).scalar()
        close_ids = [y for y in year_ids if y != keep]
        close_sql = ", ".join(str(int(y)) for y in close_ids)
        connection.execute(
            text(
                "UPDATE academic_years SET status = :closed, is_current = 0 "
                f"WHERE academic_year_id IN ({close_sql})"
            ),
            {"closed": STATUS_CLOSED},
        )
        logger.warning(
            "Startup schema migration: school %s had multiple ACTIVE academic "
            "years; kept %s and closed %s",
            school_id, keep, close_ids,
        )


def _backfill_attendance_year(connection) -> None:
    """Fill ``attendance_records.academic_year_id`` for legacy rows.

    Resolution order (each step only touches rows still NULL):

    1. the year of an enrollment that contains the attendance date;
    2. a school year that contains the attendance date;
    3. the student's most recent enrollment year;
    4. the student's school's ACTIVE/most recent year.
    """
    steps = [
        (
            "enrollment containing date",
            """
            UPDATE attendance_records
            SET academic_year_id = (
                SELECT se.academic_year_id
                FROM student_enrollments se
                JOIN academic_years y ON y.academic_year_id = se.academic_year_id
                WHERE se.student_id = attendance_records.student_id
                  AND y.start_date IS NOT NULL AND y.end_date IS NOT NULL
                  AND attendance_records.date >= y.start_date
                  AND attendance_records.date <= y.end_date
                ORDER BY y.start_date DESC
                LIMIT 1
            )
            WHERE academic_year_id IS NULL
            """,
        ),
        (
            "school year containing date",
            """
            UPDATE attendance_records
            SET academic_year_id = (
                SELECT y.academic_year_id
                FROM academic_years y
                JOIN students s ON s.school_id = y.school_id
                WHERE s.student_id = attendance_records.student_id
                  AND y.start_date IS NOT NULL AND y.end_date IS NOT NULL
                  AND attendance_records.date >= y.start_date
                  AND attendance_records.date <= y.end_date
                ORDER BY y.is_current DESC, y.start_date DESC
                LIMIT 1
            )
            WHERE academic_year_id IS NULL
            """,
        ),
        (
            "latest enrollment",
            """
            UPDATE attendance_records
            SET academic_year_id = (
                SELECT se.academic_year_id
                FROM student_enrollments se
                WHERE se.student_id = attendance_records.student_id
                ORDER BY se.enrollment_id DESC
                LIMIT 1
            )
            WHERE academic_year_id IS NULL
            """,
        ),
        (
            "school active year",
            """
            UPDATE attendance_records
            SET academic_year_id = (
                SELECT y.academic_year_id
                FROM academic_years y
                JOIN students s ON s.school_id = y.school_id
                WHERE s.student_id = attendance_records.student_id
                ORDER BY (y.status = 'ACTIVE') DESC, y.start_date DESC
                LIMIT 1
            )
            WHERE academic_year_id IS NULL
            """,
        ),
    ]
    for label, sql in steps:
        try:
            result = connection.execute(text(sql))
            if result.rowcount:
                logger.info(
                    "Startup schema migration: backfilled attendance year "
                    "(%s) for %s row(s)",
                    label, result.rowcount,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Academic year migration: attendance backfill step '%s' failed: %s",
                label, exc,
            )


def _backfill_teacher_subject_year(connection) -> None:
    """Assign ``teacher_subjects.academic_year_id`` from timetable history.

    A legacy assignment is mapped to the most recent academic year in which
    the same school/grade/section/subject combination had a timetable entry.
    When nothing maps (no timetable data) the row keeps ``NULL``, which every
    query treats as "legacy / all years" so it stays visible.
    """
    try:
        timetables = connection.execute(
            text(
                "SELECT school_id, grade_id, section_id, subject_id, academic_year_id "
                "FROM timetables "
                "WHERE academic_year_id IS NOT NULL"
            )
        ).fetchall()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Academic year migration: timetable lookup failed: %s", exc)
        return

    best: dict = {}
    for school_id, grade_id, section_id, subject_id, year_id in timetables:
        if None in (school_id, grade_id, section_id, subject_id, year_id):
            continue
        key = (school_id, grade_id, section_id, subject_id)
        current = best.get(key)
        if current is None or year_id > current:
            best[key] = year_id

    try:
        pending = connection.execute(
            text(
                "SELECT academic_year_id, school_id, grade_id, section_id, subject_id "
                "FROM teacher_subjects WHERE academic_year_id IS NULL"
            )
        ).fetchall()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Academic year migration: teacher_subjects lookup failed: %s", exc
        )
        return

    # (school, grade, section, subject) -> year already claimed by a row
    claimed: dict = {}
    for row in connection.execute(
        text(
            "SELECT school_id, grade_id, section_id, subject_id, academic_year_id "
            "FROM teacher_subjects WHERE academic_year_id IS NOT NULL"
        )
    ).fetchall():
        school_id, grade_id, section_id, subject_id, year_id = row
        claimed.setdefault(
            (school_id, grade_id, section_id, subject_id), set()
        ).add(year_id)

    updates = []
    for row in pending:
        _old_year, school_id, grade_id, section_id, subject_id = row
        key = (school_id, grade_id, section_id, subject_id)
        year_id = best.get(key)
        if year_id is None:
            continue  # no timetable evidence -> keep NULL (legacy)
        if year_id in claimed.setdefault(key, set()):
            # Another teacher already owns this subject/section/year: leave
            # this row NULL rather than inventing a year for it.
            continue
        claimed[key].add(year_id)
        updates.append((year_id, school_id, grade_id, section_id, subject_id))

    for year_id, school_id, grade_id, section_id, subject_id in updates:
        try:
            connection.execute(
                text(
                    "UPDATE teacher_subjects SET academic_year_id = :year_id "
                    "WHERE academic_year_id IS NULL AND school_id = :school_id "
                    "AND grade_id = :grade_id AND section_id = :section_id "
                    "AND subject_id = :subject_id"
                ),
                {
                    "year_id": year_id,
                    "school_id": school_id,
                    "grade_id": grade_id,
                    "section_id": section_id,
                    "subject_id": subject_id,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Academic year migration: teacher_subjects backfill failed: %s", exc
            )

    if updates:
        logger.info(
            "Startup schema migration: backfilled academic_year_id for %s "
            "teacher_subjects row(s)",
            len(updates),
        )


def _sync_school_settings(connection) -> None:
    """Make the legacy free-text ``school_settings.academic_year`` mirror the
    ACTIVE academic year instead of contradicting it.

    Only existing rows are updated - no settings row is ever created here.
    """
    try:
        result = connection.execute(
            text(
                "UPDATE school_settings ss "
                "JOIN academic_years ay ON ay.school_id = ss.school_id "
                "AND ay.status = 'ACTIVE' "
                "SET ss.academic_year = ay.year_name "
                "WHERE NOT (ss.academic_year <=> ay.year_name)"
            )
        )
        if result.rowcount:
            logger.info(
                "Startup schema migration: synced school_settings.academic_year "
                "for %s school(s)",
                result.rowcount,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Academic year migration: school_settings sync failed: %s", exc
        )


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def apply_academic_year_migrations(bind=None) -> None:
    """Apply the Academic Year schema/data reconciliation (idempotent).

    ``bind`` is the engine to work on; defaults to the application engine.
    Invoked from the Alembic legacy-repair migration - no longer at import
    time of ``main.py``.
    """
    if bind is None:
        from app.core.database import engine as app_engine

        bind = app_engine

    def _guard(fn, label: str):
        def _run():
            with bind.begin() as connection:
                fn(connection)

        _step(_run, label)

    # --- columns (normally already added by the generic reconciler, but the
    # # NOT NULL status column needs an explicit server default on old MySQL
    # configurations) -----------------------------------------------------
    _guard(
        lambda c: _ensure_column(
            c, "academic_years", "status", "VARCHAR(20) NOT NULL DEFAULT 'UPCOMING'"
        ),
        "academic_years.status column",
    )
    _guard(
        lambda c: _ensure_column(c, "attendance_records", "academic_year_id", "INT NULL"),
        "attendance_records.academic_year_id column",
    )
    _guard(
        lambda c: _ensure_column(c, "teacher_subjects", "academic_year_id", "INT NULL"),
        "teacher_subjects.academic_year_id column",
    )

    # --- backfills --------------------------------------------------------
    _guard(_backfill_status, "academic_years.status backfill")
    _guard(_repair_single_active, "single ACTIVE year repair")
    _guard(_backfill_attendance_year, "attendance academic_year_id backfill")
    _guard(_backfill_teacher_subject_year, "teacher_subjects academic_year_id backfill")

    # --- indexes ----------------------------------------------------------
    _guard(
        lambda c: _ensure_index(c, "academic_years", "ix_academic_years_status", ["status"]),
        "academic_years.status index",
    )
    _guard(
        lambda c: _ensure_index(
            c, "attendance_records", "ix_attendance_records_academic_year_id",
            ["academic_year_id"],
        ),
        "attendance_records.academic_year_id index",
    )
    _guard(
        lambda c: _ensure_index(
            c, "attendance_records", "idx_attendance_year_section_date",
            ["academic_year_id", "section_id", "date"],
        ),
        "attendance year/section/date index",
    )
    _guard(
        lambda c: _ensure_index(
            c, "teacher_subjects", "ix_teacher_subjects_academic_year_id",
            ["academic_year_id"],
        ),
        "teacher_subjects.academic_year_id index",
    )

    # --- foreign keys -----------------------------------------------------
    _guard(
        lambda c: _ensure_foreign_key(
            c, "attendance_records", "academic_year_id",
            "academic_years", "academic_year_id",
        ),
        "attendance_records.academic_year_id FK",
    )
    _guard(
        lambda c: _ensure_foreign_key(
            c, "teacher_subjects", "academic_year_id",
            "academic_years", "academic_year_id",
        ),
        "teacher_subjects.academic_year_id FK",
    )

    # --- unique constraints ----------------------------------------------
    _guard(
        lambda c: _ensure_unique(
            c,
            "student_enrollments",
            "uq_student_year_enrollment",
            ["student_id", "academic_year_id"],
            """
            SELECT student_id, academic_year_id, COUNT(*) AS c
            FROM student_enrollments
            GROUP BY student_id, academic_year_id
            HAVING c > 1
            """,
        ),
        "student_enrollments one-row-per-year constraint",
    )
    # Only swap the teacher_subjects unique index once the backfill above has
    # produced data that actually satisfies the new rule.
    def _swap_teacher_subject_unique(connection) -> None:
        if "uq_teacher_subject_year_class_subject" in _index_names(
            connection, "teacher_subjects"
        ):
            return
        dupes = _duplicate_groups(
            connection,
            """
            SELECT school_id, academic_year_id, grade_id, section_id, subject_id, COUNT(*) AS c
            FROM teacher_subjects
            WHERE academic_year_id IS NOT NULL
            GROUP BY school_id, academic_year_id, grade_id, section_id, subject_id
            HAVING c > 1
            """,
        )
        if dupes:
            logger.error(
                "Academic year migration: NOT swapping teacher_subjects unique "
                "index; two teachers already share a subject/section/year: %s",
                dupes[:5],
            )
            return
        _drop_unique_if_exists(
            connection, "teacher_subjects", "uq_teacher_subject_grade_section_school"
        )
        connection.execute(
            text(
                "ALTER TABLE `teacher_subjects` ADD CONSTRAINT "
                "`uq_teacher_subject_year_class_subject` UNIQUE "
                "(`school_id`, `academic_year_id`, `grade_id`, `section_id`, `subject_id`)"
            )
        )
        logger.info(
            "Startup schema migration: teacher_subjects unique index now scoped "
            "by academic year"
        )

    _guard(_swap_teacher_subject_unique, "teacher_subjects unique index swap")

    # --- keep the legacy free-text setting in agreement --------------------
    _guard(_sync_school_settings, "school_settings.academic_year sync")
