"""slip tests

Adds the single table backing the Slip Tests feature:

  * slip_tests - a short, low-stakes assessment scheduled by a subject teacher
                 for one grade + section + subject inside one academic year.

Purely additive: nothing existing is altered, dropped or rewritten. Results
recording is deliberately out of scope; a future ``slip_test_results`` table
will link to ``slip_tests.id`` and reuse ``max_marks``.

Mirrors the hand-run script ``backend-python/slip_tests_migration.sql``. Both
are written so running either one twice is a no-op:
``_create_table``/``_create_index`` skip work that already exists, so this
revision is safe on a database where the SQL script was applied by hand (and
vice versa - the SQL script's ``CREATE TABLE IF NOT EXISTS`` skips an existing
table).

Timezone policy: ``scheduled_date``/``start_time`` are plain school-local values
and are never shifted through UTC. ``created_at``/``updated_at`` follow the
project-wide naive-UTC convention (``app/core/time_utils.py``).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-04
"""
from typing import Sequence, Union

import sqlalchemy as _sa
from alembic import op as _op
from alembic import op


def _inspector():
    return _sa.inspect(_op.get_bind())


def _table_exists(name: str) -> bool:
    return _inspector().has_table(name)


def _index_exists(table: str, name: str) -> bool:
    try:
        return any(ix["name"] == name for ix in _inspector().get_indexes(table))
    except Exception:
        return False


def upgrade() -> None:
    if not _table_exists("slip_tests"):
        op.create_table(
            "slip_tests",
            _sa.Column("id", _sa.Integer(), autoincrement=True, nullable=False),
            _sa.Column("school_id", _sa.Integer(), nullable=False),
            _sa.Column("academic_year_id", _sa.Integer(), nullable=False),
            _sa.Column("grade_id", _sa.Integer(), nullable=False),
            _sa.Column("section_id", _sa.Integer(), nullable=False),
            _sa.Column("subject_id", _sa.Integer(), nullable=False),
            _sa.Column("teacher_id", _sa.Integer(), nullable=False),
            _sa.Column("title", _sa.String(length=150), nullable=False),
            _sa.Column("description", _sa.Text(), nullable=True),
            _sa.Column("scheduled_date", _sa.Date(), nullable=False),
            _sa.Column("start_time", _sa.Time(), nullable=True),
            _sa.Column("duration_minutes", _sa.Integer(), nullable=True),
            _sa.Column("max_marks", _sa.Integer(), nullable=False),
            _sa.Column(
                "status",
                _sa.Enum("scheduled", "cancelled", "completed", name="slip_test_status"),
                nullable=False,
                server_default="scheduled",
            ),
            _sa.Column("created_at", _sa.DateTime(), nullable=False),
            _sa.Column("updated_at", _sa.DateTime(), nullable=False),
            _sa.PrimaryKeyConstraint("id"),
            _sa.CheckConstraint("max_marks > 0", name="ck_slip_tests_max_marks"),
            _sa.CheckConstraint(
                "duration_minutes IS NULL OR duration_minutes > 0",
                name="ck_slip_tests_duration",
            ),
        )

        _table = "slip_tests"
        for name, cols in (
            ("ix_slip_tests_id", ["id"]),
            ("ix_slip_tests_school_id", ["school_id"]),
            ("ix_slip_tests_academic_year_id", ["academic_year_id"]),
            ("ix_slip_tests_grade_id", ["grade_id"]),
            ("ix_slip_tests_section_id", ["section_id"]),
            ("ix_slip_tests_subject_id", ["subject_id"]),
            ("ix_slip_tests_teacher_id", ["teacher_id"]),
            ("ix_slip_tests_status", ["status"]),
            (
                "ix_slip_tests_school_year_class_date",
                ["school_id", "academic_year_id", "grade_id", "section_id", "scheduled_date"],
            ),
            ("ix_slip_tests_teacher_date", ["teacher_id", "scheduled_date"]),
        ):
            if not _index_exists(_table, name):
                op.create_index(name, _table, cols)

        op.create_foreign_key(
            "slip_tests_ibfk_1", "slip_tests", "schools", ["school_id"], ["school_id"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "slip_tests_ibfk_2", "slip_tests", "academic_years",
            ["academic_year_id"], ["academic_year_id"], ondelete="CASCADE",
        )
        op.create_foreign_key(
            "slip_tests_ibfk_3", "slip_tests", "grades", ["grade_id"], ["grade_id"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "slip_tests_ibfk_4", "slip_tests", "sections", ["section_id"], ["section_id"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "slip_tests_ibfk_5", "slip_tests", "subjects", ["subject_id"], ["subject_id"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "slip_tests_ibfk_6", "slip_tests", "teachers", ["teacher_id"], ["teacher_id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    # Development / verified-rollback only. Slip test data is business data, so
    # production rollbacks should prefer a forward fix.
    if _table_exists("slip_tests"):
        op.drop_table("slip_tests")


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None