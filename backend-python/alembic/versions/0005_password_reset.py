"""password reset - OTP self service + admin assisted queue

Adds the two tables that back the password-recovery flows and the flag that
forces a first login to pick a new password:

  * password_reset_otps       - one row per requested 6-digit code. Stores an
                                HMAC-SHA256 of the code (never the code) plus
                                expiry, wrong-attempt counter, source IP, and
                                after verification the SHA-256 hash of the
                                single-use reset token.
  * password_reset_requests   - the staff work queue for accounts with no
                                email (mainly students): pending/completed/
                                rejected, who handled it and when.
  * users.must_change_password- already present on databases created by
                                0001/0002; added here only when missing so a
                                hand-managed ``vshs_db`` cannot be left behind.

Purely additive: nothing existing is altered or dropped. Mirrors the hand-run
script ``backend-python/password_reset_migration.sql``; both are written so
running either twice is a no-op (every CREATE is existence-guarded and the
column add checks ``information_schema`` first), which means it is safe on a
database where the other was already applied by hand.

Timezone policy: every timestamp column is naive UTC (``datetime.utcnow`` house
style), see ``app/core/time_utils.py``.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-04
"""
from typing import Sequence, Union

import sqlalchemy as _sa
from alembic import op as _op


def _inspector():
    return _sa.inspect(_op.get_bind())


def _table_exists(name: str) -> bool:
    return _inspector().has_table(name)


def _index_exists(table: str, name: str) -> bool:
    try:
        return any(ix["name"] == name for ix in _inspector().get_indexes(table))
    except Exception:
        return False


def _column_exists(table: str, name: str) -> bool:
    try:
        return any(col["name"] == name for col in _inspector().get_columns(table))
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
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. password_reset_otps - hashed codes + hashed single-use token
    # ------------------------------------------------------------------
    _create_table(
        "password_reset_otps",
        _sa.Column("id", _sa.Integer(), autoincrement=True, nullable=False),
        _sa.Column("user_id", _sa.Integer(), nullable=False),
        _sa.Column("otp_hash", _sa.String(length=128), nullable=False),
        _sa.Column("expires_at", _sa.DateTime(), nullable=False),
        _sa.Column("attempts", _sa.Integer(), server_default="0", nullable=False),
        _sa.Column("used_at", _sa.DateTime(), nullable=True),
        _sa.Column("created_at", _sa.DateTime(), nullable=False),
        _sa.Column("request_ip", _sa.String(length=45), nullable=True),
        _sa.Column("reset_token_hash", _sa.String(length=64), nullable=True),
        _sa.Column("reset_token_expires_at", _sa.DateTime(), nullable=True),
        _sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        _sa.PrimaryKeyConstraint("id"),
    )
    _create_index("ix_password_reset_otps_id", "password_reset_otps", ["id"])
    _create_index("ix_password_reset_otps_user_id", "password_reset_otps", ["user_id"])
    _create_index(
        "ix_password_reset_otps_reset_token_hash",
        "password_reset_otps",
        ["reset_token_hash"],
    )

    # ------------------------------------------------------------------
    # 2. password_reset_requests - staff work queue (Flow B)
    # ------------------------------------------------------------------
    _create_table(
        "password_reset_requests",
        _sa.Column("id", _sa.Integer(), autoincrement=True, nullable=False),
        _sa.Column("user_id", _sa.Integer(), nullable=False),
        _sa.Column(
            "status",
            _sa.Enum("pending", "completed", "rejected", name="password_reset_request_status"),
            server_default="pending",
            nullable=False,
        ),
        _sa.Column("requested_at", _sa.DateTime(), nullable=False),
        _sa.Column("handled_by", _sa.Integer(), nullable=True),
        _sa.Column("handled_at", _sa.DateTime(), nullable=True),
        _sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        _sa.ForeignKeyConstraint(["handled_by"], ["users.user_id"], ondelete="SET NULL"),
        _sa.PrimaryKeyConstraint("id"),
    )
    _create_index("ix_password_reset_requests_id", "password_reset_requests", ["id"])
    _create_index("ix_password_reset_requests_user_id", "password_reset_requests", ["user_id"])
    _create_index("ix_password_reset_requests_status", "password_reset_requests", ["status"])

    # ------------------------------------------------------------------
    # 3. users.must_change_password (no-op on any database at 0001+)
    # ------------------------------------------------------------------
    if _column_exists("users", "must_change_password"):
        return
    _op.execute(
        "ALTER TABLE `users` "
        "ADD COLUMN `must_change_password` TINYINT(1) NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    """Drops only the two tables this revision created.

    ``users.must_change_password`` is deliberately NOT dropped: the column is
    owned by revision 0001 on every standard database (and by 0002's repair on
    legacy ones), and dropping it would break the login contract there.
    Guarded so a downgrade on a database that never had these tables is a no-op.

    Tables are dropped BEFORE their indexes: MySQL refuses to drop an index
    that a foreign key constraint still needs, and ``DROP TABLE`` removes
    the indexes with it. The ``_drop_index`` calls below are guarded no-ops
    kept for symmetry.
    """
    _drop_table("password_reset_requests")
    _drop_table("password_reset_otps")

    _drop_index("ix_password_reset_requests_status", "password_reset_requests")
    _drop_index("ix_password_reset_requests_user_id", "password_reset_requests")
    _drop_index("ix_password_reset_requests_id", "password_reset_requests")

    _drop_index("ix_password_reset_otps_reset_token_hash", "password_reset_otps")
    _drop_index("ix_password_reset_otps_user_id", "password_reset_otps")
    _drop_index("ix_password_reset_otps_id", "password_reset_otps")
