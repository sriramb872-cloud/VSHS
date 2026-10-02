"""legacy schema repair

Runs the relocated legacy-database reconciliation exactly once, inside the
Alembic chain (previously it executed at *import time* of ``main.py`` on
every gunicorn worker boot).

``app.core.schema_repair.repair_database`` is strictly additive and
idempotent: it creates missing tables, adds missing columns, widens ENUMs,
backfills academic-year references, swaps legacy unique keys and reconciles
the academic-year lifecycle.  It never drops or rewrites user data.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use the engine behind the active Alembic connection so the repair runs
    # against exactly the database being migrated.
    from app.core.schema_repair import repair_database

    engine = op.get_bind().engine
    repair_database(engine)


def downgrade() -> None:
    # Deliberate no-op: the repair only ever *adds* schema/data (new tables,
    # columns, widened ENUMs, backfills, index swaps).  Reverting it would
    # mean destroying schema that may now hold data written by the current
    # application version, so there is nothing safe to undo.
    pass
