"""web push subscriptions

Adds the single table backing Web Push (VAPID) delivery:

  * push_subscriptions - one row per browser subscription, bound to the
                        user account that enabled it. The push endpoint is
                        stored in full but indexed through its SHA-256 hash
                        (``endpoint_hash``) because MySQL cannot index a
                        long TEXT column; the hash is UNIQUE so a shared
                        school device upserts instead of duplicating.

Purely additive: nothing existing is altered, dropped or rewritten. Every
CREATE is existence-guarded (same style as 0003/0004/0005), so the
revision is safe to re-run and on a database where the table was created
by hand.

Timezone policy: ``created_at``/``last_used_at`` are naive UTC
(``datetime.utcnow`` house style); see ``app/core/time_utils.py``.

Revision ID: 0006
Revises: 0005
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


def _create_table(name: str, *args, **kwargs) -> None:
    if not _table_exists(name):
        _op.create_table(name, *args, **kwargs)


def _create_index(name: str, table: str, columns, **kwargs) -> None:
    if not _table_exists(table) or _index_exists(table, name):
        return
    _op.create_index(name, table, columns, **kwargs)


def _drop_index(name: str, table: str) -> None:
    if _table_exists(table) and _index_exists(table, name):
        _op.drop_index(name, table_name=table)


def _drop_table(name: str) -> None:
    if _table_exists(name):
        _op.drop_table(name)


# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. push_subscriptions - browser push endpoints per user
    # ------------------------------------------------------------------
    _create_table(
        "push_subscriptions",
        _sa.Column("id", _sa.Integer(), autoincrement=True, nullable=False),
        _sa.Column("user_id", _sa.Integer(), nullable=False),
        _sa.Column("endpoint", _sa.Text(), nullable=False),
        _sa.Column("endpoint_hash", _sa.String(length=64), nullable=False),
        _sa.Column("p256dh", _sa.String(length=255), nullable=False),
        _sa.Column("auth", _sa.String(length=255), nullable=False),
        _sa.Column("user_agent", _sa.String(length=255), nullable=True),
        _sa.Column("created_at", _sa.DateTime(), nullable=False),
        _sa.Column("last_used_at", _sa.DateTime(), nullable=True),
        _sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        _sa.PrimaryKeyConstraint("id"),
    )
    _create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])
    # UNIQUE: the model declares unique=True on this column, which
    # SQLAlchemy renders as a unique index (no separate constraint).
    _create_index(
        "ix_push_subscriptions_endpoint_hash",
        "push_subscriptions",
        ["endpoint_hash"],
        unique=True,
    )


def downgrade() -> None:
    """Drops only the table this revision created. Guarded so a downgrade on
    a database that never had it is a no-op.

    The table is dropped BEFORE its indexes: MySQL refuses to drop an index
    that a foreign key constraint still needs (``ix_push_subscriptions_user_id``
    backs the ``user_id`` FK), and ``DROP TABLE`` removes the indexes with
    it. The ``_drop_index`` calls below are guarded no-ops kept for symmetry.
    """
    _drop_table("push_subscriptions")
    _drop_index("ix_push_subscriptions_endpoint_hash", "push_subscriptions")
    _drop_index("ix_push_subscriptions_user_id", "push_subscriptions")
