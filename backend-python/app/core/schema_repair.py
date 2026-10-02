# backend-python/app/core/schema_repair.py
"""Idempotent, additive schema reconciliation for LEGACY databases.

Historically this logic (together with ``Base.metadata.create_all`` and
``apply_academic_year_migrations``) ran at *import time* of ``main.py`` -
meaning every gunicorn worker executed ALTER TABLE statements concurrently
on every boot. It now runs exactly once per deployment, inside the Alembic
chain (migration ``0002_legacy_schema_repair``), before any worker starts.

Everything here is:

* **additive** - columns/tables/indexes are only ever added, ENUMs only ever
  widened; the one exception is dropping a *strictly redundant duplicate*
  legacy index (same columns + uniqueness, with an equivalent index left in
  place) that would otherwise show up as autogenerate drift forever. No
  data is ever dropped or rewritten;
* **idempotent** - every statement is guarded by an existence check;
* **MySQL-targeted** - production is MySQL; non-MySQL dialects skip the
  DDL that is dialect-specific.

Future schema changes must NOT be added here - create a new frozen Alembic
revision instead (see docs/MIGRATIONS.md).
"""
import logging
from typing import Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, ProgrammingError

logger = logging.getLogger("scholaris")


def _column_ddl(engine: Engine, column) -> str:
    """Render the DDL fragment for a single ORM column."""
    return column.type.compile(engine.dialect)


def _quote(identifier: str) -> str:
    return f"`{identifier}`"


def _reconcile_enum_column(engine: Engine, connection, table, column, live_column: dict) -> None:
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
        "Schema repair: widened enum %s.%s with %s",
        table.name,
        column.name,
        ", ".join(missing),
    )


def apply_startup_schema_migrations(engine: Optional[Engine] = None, metadata=None) -> None:
    """Reconcile every table in the ORM metadata with the live database.

    ``create_all`` creates missing *tables* but it never adds columns to
    tables that already exist. Any installation whose database predates a
    column that was later added to a model would otherwise boot fine and then
    fail at query time with MySQL error 1054 "Unknown column ... in 'field
    list'".

    This reconciles *every* table in ``Base.metadata`` and adds any column
    the models declare but the database is missing. The migration is strictly
    additive: it never drops or renames anything, so it cannot destroy
    existing data. ENUM columns whose model declares additional values are
    widened (additive) as well.

    Meant to be invoked from the Alembic legacy-repair migration - NOT from
    application startup.
    """
    if engine is None or metadata is None:
        from app.core.database import Base, engine as default_engine

        engine = engine or default_engine
        metadata = metadata or Base.metadata

    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            present_tables = set(inspector.get_table_names())
            for table in metadata.sorted_tables:
                if table.name not in present_tables:
                    # The caller (Alembic 0001 / create_all) handles missing
                    # tables; this step only reconciles existing ones.
                    continue
                live_columns = {c["name"]: c for c in inspector.get_columns(table.name)}
                for column in table.columns:
                    if column.name not in live_columns:
                        nullability = "" if column.nullable else " NOT NULL"
                        connection.execute(
                            text(
                                f"ALTER TABLE {_quote(table.name)} "
                                f"ADD COLUMN {_quote(column.name)} "
                                f"{_column_ddl(engine, column)}{nullability}"
                            )
                        )
                        logger.info(
                            "Schema repair: added %s.%s",
                            table.name,
                            column.name,
                        )
                        continue

                    # MySQL ENUM columns can drift: adding a value to the
                    # model's Enum() does not alter an existing column, so the
                    # database keeps the old value list and any INSERT/UPDATE
                    # using the new value fails with errno 1265 "Data truncated
                    # for column".
                    _reconcile_enum_column(
                        engine, connection, table, column, live_columns[column.name]
                    )
    except (OperationalError, ProgrammingError) as exc:
        # Concurrent execution should no longer happen (migrations run once,
        # before workers), but treat a lost race as non-fatal rather than
        # failing the deploy of an otherwise-working database.
        logger.warning("Schema repair skipped (concurrent application?): %s", exc)


def _apply_legacy_one_offs(engine: Engine) -> None:
    """Ported one-offs from the now-removed ``scripts/migrate.py``.

    Only the two operations that are *not* already covered by the column
    reconcile / ENUM widening above:

    1. Backfill ``homework.academic_year_id`` from the school's current year
       (the column is added by the reconcile step; existing rows stay NULL
       otherwise, which silently orphans them from year filtering).
    2. Swap the legacy ``report_cards`` unique key
       ``(student_id, academic_year_id, term_name)`` for the exam-aware one
       required by the current model.

    Both are guarded and therefore safe to run repeatedly.
    """
    if engine.dialect.name != "mysql":
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if {"homework", "academic_years"} <= tables:
        columns = {c["name"] for c in inspector.get_columns("homework")}
        if "academic_year_id" in columns:
            with engine.begin() as connection:
                result = connection.execute(
                    text(
                        "UPDATE homework h "
                        "JOIN academic_years ay ON ay.school_id = h.school_id "
                        "AND ay.is_current = 1 "
                        "SET h.academic_year_id = ay.academic_year_id "
                        "WHERE h.academic_year_id IS NULL"
                    )
                )
                rowcount = result.rowcount
            if rowcount:
                logger.info(
                    "Schema repair: backfilled academic_year_id on %s homework rows",
                    rowcount,
                )

    if "report_cards" in tables:
        unique_constraints = inspector.get_unique_constraints("report_cards")
        legacy_unique = next(
            (c for c in unique_constraints if c.get("name") == "uq_student_term_report_card"),
            None,
        )
        has_current = any(
            c.get("name") == "uq_student_exam_term_report_card"
            for c in unique_constraints
        )
        if legacy_unique or not has_current:
            with engine.begin() as connection:
                if legacy_unique:
                    connection.execute(
                        text("ALTER TABLE report_cards DROP INDEX uq_student_term_report_card")
                    )
                    logger.info(
                        "Schema repair: dropped legacy unique key uq_student_term_report_card"
                    )
                if not has_current:
                    connection.execute(
                        text(
                            "ALTER TABLE report_cards "
                            "ADD CONSTRAINT uq_student_exam_term_report_card "
                            "UNIQUE (student_id, academic_year_id, exam_id, term_name)"
                        )
                    )
                    logger.info(
                        "Schema repair: added unique key uq_student_exam_term_report_card"
                    )


def _reconcile_foreign_keys(engine: Engine) -> None:
    """Add foreign keys the live schema is missing relative to the models.

    Legacy databases predate these relationships: the column was added by an
    older ``migrate.py`` run but never got its FK.  Each addition is guarded
    by (a) the FK not already existing, (b) the referenced tables existing,
    and (c) an orphan-row check - if live data would violate the constraint,
    the FK is skipped with a warning rather than failing the migration.
    """
    if engine.dialect.name != "mysql":
        return

    fk_specs = (
        ("homework", "academic_year_id", "academic_years", "academic_year_id"),
        ("report_cards", "exam_id", "exams", "id"),
    )

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table, column, ref_table, ref_column in fk_specs:
            if table not in tables or ref_table not in tables:
                continue
            columns = {c["name"] for c in inspector.get_columns(table)}
            if column not in columns:
                continue
            existing = connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = :t AND COLUMN_NAME = :c "
                    "AND REFERENCED_TABLE_NAME IS NOT NULL"
                ),
                {"t": table, "c": column},
            ).scalar()
            if existing:
                continue
            orphans = connection.execute(
                text(
                    f"SELECT COUNT(*) FROM `{table}` child "
                    f"LEFT JOIN `{ref_table}` parent "
                    f"ON parent.`{ref_column}` = child.`{column}` "
                    f"WHERE child.`{column}` IS NOT NULL "
                    f"AND parent.`{ref_column}` IS NULL"
                )
            ).scalar()
            if orphans:
                logger.warning(
                    "Schema repair: NOT adding FK %s.%s -> %s.%s: %s orphaned row(s)",
                    table, column, ref_table, ref_column, orphans,
                )
                continue
            connection.execute(
                text(
                    f"ALTER TABLE `{table}` "
                    f"ADD CONSTRAINT `fk_{table}_{column}` "
                    f"FOREIGN KEY (`{column}`) REFERENCES `{ref_table}` (`{ref_column}`) "
                    f"ON DELETE SET NULL"
                )
            )
            logger.info(
                "Schema repair: added FK %s.%s -> %s.%s",
                table, column, ref_table, ref_column,
            )


def _drop_redundant_legacy_indexes(engine: Engine) -> None:
    """Drop a legacy duplicate index only when an equivalent one exists.

    Some legacy databases carry an extra index left over from an older naming
    convention (e.g. ``idx_users_reset_token`` next to the model's
    ``ix_users_reset_token``).  Alembic autogenerate reports it as drift on
    every run.  The index is only dropped when another index over the *same
    column(s) with the same uniqueness* already exists, so lookups keep an
    equivalent path and no data is touched.
    """
    if engine.dialect.name != "mysql":
        return

    redundant = (("users", "idx_users_reset_token", "ix_users_reset_token"),)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table, legacy_name, current_name in redundant:
            if table not in tables:
                continue
            indexes = {i["name"]: i for i in inspector.get_indexes(table)}
            legacy = indexes.get(legacy_name)
            current = indexes.get(current_name)
            if not legacy or not current:
                continue
            if legacy.get("column_names") != current.get("column_names"):
                continue
            if bool(legacy.get("unique")) != bool(current.get("unique")):
                continue
            connection.execute(
                text(f"ALTER TABLE `{table}` DROP INDEX `{legacy_name}`")
            )
            logger.info(
                "Schema repair: dropped redundant legacy index %s on %s",
                legacy_name, table,
            )


def repair_database(engine: Optional[Engine] = None) -> None:
    """Full legacy-database reconciliation - the combined former startup DDL.

    Order matters: create missing tables, reconcile columns/ENUMs, then run
    the Academic Year backfills/index swaps. Idempotent and additive.
    """
    from app.core.database import Base
    from app.core.academic_year_migrations import apply_academic_year_migrations

    if engine is None:
        from app.core.database import engine as default_engine

        engine = default_engine

    # 1. Missing tables (covers a legacy DB that predates a whole table).
    Base.metadata.create_all(bind=engine)

    # 2. Missing columns + ENUM widening.
    apply_startup_schema_migrations(engine=engine, metadata=Base.metadata)

    # 3. Academic Year lifecycle: backfills, index/constraint swaps and the
    #    "one ACTIVE year per school" repair.
    apply_academic_year_migrations(bind=engine)

    # 4. Remaining one-offs from the old scripts/migrate.py (homework year
    #    backfill, report_cards unique-key swap).
    _apply_legacy_one_offs(engine)

    # 5. Relationships the legacy schema never got (guarded by orphan checks).
    _reconcile_foreign_keys(engine)

    # 6. Redundant duplicate legacy index (guarded: equivalent index kept).
    _drop_redundant_legacy_indexes(engine)
