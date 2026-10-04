"""subscription module

Adds the six tables of the Subscription & Access Control module:

  * subscription_plans          - per-school, per-role pricing catalogue
  * subscriptions               - user entitlements (paid time windows)
  * school_subscription_settings- per-school enable/disable + school-wide free
  * user_subscription_overrides - per-user free overrides (auditable)
  * subscription_payments       - append-only payment records
  * subscription_audit_logs     - audit trail for billing/access decisions

Why every CREATE is guarded
---------------------------
Revision 0002 runs ``app.core.schema_repair.repair_database``, which ends
with ``Base.metadata.create_all``.  On a *fresh* database that already
creates these six tables (the models are registered in ``Base.metadata``),
while a *production* database that was stamped at 0002 before this module
existed does not have them.  The existence guards make this revision correct
in both directions and keep it safe to re-run: it is strictly additive
(never drops or rewrites existing data).

Timezone policy: every timestamp column is stored as naive UTC
(``datetime.utcnow`` house style); see ``app.core.time_utils``.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-01
"""
from typing import Sequence, Union

from alembic import op as _op
from alembic import op
import sqlalchemy as sa
import sqlalchemy as _sa


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
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. subscription_plans - pricing catalogue (never hard-deleted)
    # ------------------------------------------------------------------
    _create_table(
        'subscription_plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='INR', nullable=False),
        sa.Column('billing_interval', sa.String(length=20), server_default='CUSTOM', nullable=False),
        sa.Column('duration_value', sa.Integer(), nullable=False),
        sa.Column('duration_unit', sa.String(length=10), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['school_id'], ['schools.school_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    _create_index(op.f('ix_subscription_plans_id'), 'subscription_plans', ['id'], unique=False)
    _create_index(op.f('ix_subscription_plans_school_id'), 'subscription_plans', ['school_id'], unique=False)
    _create_index(op.f('ix_subscription_plans_role'), 'subscription_plans', ['role'], unique=False)
    _create_index('ix_subscription_plans_school_role', 'subscription_plans', ['school_id', 'role'], unique=False)
    _create_index('ix_subscription_plans_school_active', 'subscription_plans', ['school_id', 'is_active'], unique=False)

    # ------------------------------------------------------------------
    # 2. school_subscription_settings - enable/disable + school-wide free
    # ------------------------------------------------------------------
    _create_table(
        'school_subscription_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('subscriptions_enabled', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('free_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['school_id'], ['schools.school_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    _create_index(op.f('ix_school_subscription_settings_id'), 'school_subscription_settings', ['id'], unique=False)
    _create_index(
        op.f('ix_school_subscription_settings_school_id'),
        'school_subscription_settings',
        ['school_id'],
        unique=True,
    )

    # ------------------------------------------------------------------
    # 3. user_subscription_overrides - per-user free overrides
    # ------------------------------------------------------------------
    _create_table(
        'user_subscription_overrides',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('override_type', sa.String(length=30), server_default='FREE', nullable=False),
        sa.Column('free_until', sa.DateTime(), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['school_id'], ['schools.school_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    _create_index(op.f('ix_user_subscription_overrides_id'), 'user_subscription_overrides', ['id'], unique=False)
    _create_index(op.f('ix_user_subscription_overrides_school_id'), 'user_subscription_overrides', ['school_id'], unique=False)
    _create_index(op.f('ix_user_subscription_overrides_user_id'), 'user_subscription_overrides', ['user_id'], unique=False)
    _create_index('uq_user_subscription_override_type', 'user_subscription_overrides', ['user_id', 'override_type'], unique=True)

    # ------------------------------------------------------------------
    # 4. subscriptions - entitlements (references the plans above)
    # ------------------------------------------------------------------
    _create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('start_at', sa.DateTime(), nullable=False),
        sa.Column('end_at', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(length=30), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['school_id'], ['schools.school_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    _create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
    _create_index(op.f('ix_subscriptions_school_id'), 'subscriptions', ['school_id'], unique=False)
    _create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    _create_index(op.f('ix_subscriptions_plan_id'), 'subscriptions', ['plan_id'], unique=False)
    _create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)
    _create_index(op.f('ix_subscriptions_end_at'), 'subscriptions', ['end_at'], unique=False)
    _create_index('ix_subscriptions_user_status', 'subscriptions', ['user_id', 'status'], unique=False)
    _create_index('ix_subscriptions_school_status', 'subscriptions', ['school_id', 'status'], unique=False)
    _create_index('ix_subscriptions_status_end', 'subscriptions', ['status', 'end_at'], unique=False)

    # ------------------------------------------------------------------
    # 5. subscription_payments - append-only financial records
    # ------------------------------------------------------------------
    _create_table(
        'subscription_payments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('plan_id', sa.Integer(), nullable=True),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='INR', nullable=False),
        sa.Column('provider', sa.String(length=20), server_default='INTERNAL', nullable=False),
        sa.Column('provider_order_id', sa.String(length=100), nullable=True),
        sa.Column('provider_payment_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['school_id'], ['schools.school_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    _create_index(op.f('ix_subscription_payments_id'), 'subscription_payments', ['id'], unique=False)
    _create_index(op.f('ix_subscription_payments_school_id'), 'subscription_payments', ['school_id'], unique=False)
    _create_index(op.f('ix_subscription_payments_user_id'), 'subscription_payments', ['user_id'], unique=False)
    _create_index(op.f('ix_subscription_payments_plan_id'), 'subscription_payments', ['plan_id'], unique=False)
    _create_index(op.f('ix_subscription_payments_subscription_id'), 'subscription_payments', ['subscription_id'], unique=False)
    _create_index(op.f('ix_subscription_payments_status'), 'subscription_payments', ['status'], unique=False)
    _create_index('ix_subscription_payments_school_status', 'subscription_payments', ['school_id', 'status'], unique=False)
    _create_index('ix_subscription_payments_user_created', 'subscription_payments', ['user_id', 'created_at'], unique=False)
    _create_index('uq_subscription_payment_order', 'subscription_payments', ['provider', 'provider_order_id'], unique=True)
    _create_index('uq_subscription_payment_provider_ref', 'subscription_payments', ['provider', 'provider_payment_id'], unique=True)

    # ------------------------------------------------------------------
    # 6. subscription_audit_logs - billing/access decision trail
    # ------------------------------------------------------------------
    _create_table(
        'subscription_audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('admin_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=60), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['school_id'], ['schools.school_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    _create_index(op.f('ix_subscription_audit_logs_id'), 'subscription_audit_logs', ['id'], unique=False)
    _create_index(op.f('ix_subscription_audit_logs_school_id'), 'subscription_audit_logs', ['school_id'], unique=False)
    _create_index(op.f('ix_subscription_audit_logs_user_id'), 'subscription_audit_logs', ['user_id'], unique=False)
    _create_index(op.f('ix_subscription_audit_logs_admin_id'), 'subscription_audit_logs', ['admin_id'], unique=False)
    _create_index(op.f('ix_subscription_audit_logs_created_at'), 'subscription_audit_logs', ['created_at'], unique=False)
    _create_index('ix_subscription_audit_school_action', 'subscription_audit_logs', ['school_id', 'action'], unique=False)
    _create_index('ix_subscription_audit_user_created', 'subscription_audit_logs', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    """Drops only the six subscription tables created by this revision.

    Payment and audit history are business records: run this only on
    databases where the module was never used.  Guarded so a downgrade on a
    database that never had the tables is a no-op.

    Tables are dropped BEFORE their indexes: MySQL refuses to drop an index
    that a foreign key constraint still needs, and ``DROP TABLE`` removes
    the indexes with it. The ``_drop_index`` calls below are guarded no-ops
    kept for symmetry.
    """
    _drop_table('subscription_audit_logs')
    _drop_table('subscription_payments')
    _drop_table('subscriptions')
    _drop_table('user_subscription_overrides')
    _drop_table('school_subscription_settings')
    _drop_table('subscription_plans')

    _drop_index('ix_subscription_audit_user_created', 'subscription_audit_logs')
    _drop_index('ix_subscription_audit_school_action', 'subscription_audit_logs')
    _drop_index(op.f('ix_subscription_audit_logs_created_at'), 'subscription_audit_logs')
    _drop_index(op.f('ix_subscription_audit_logs_admin_id'), 'subscription_audit_logs')
    _drop_index(op.f('ix_subscription_audit_logs_user_id'), 'subscription_audit_logs')
    _drop_index(op.f('ix_subscription_audit_logs_school_id'), 'subscription_audit_logs')
    _drop_index(op.f('ix_subscription_audit_logs_id'), 'subscription_audit_logs')

    _drop_index('uq_subscription_payment_provider_ref', 'subscription_payments')
    _drop_index('uq_subscription_payment_order', 'subscription_payments')
    _drop_index('ix_subscription_payments_user_created', 'subscription_payments')
    _drop_index('ix_subscription_payments_school_status', 'subscription_payments')
    _drop_index(op.f('ix_subscription_payments_status'), 'subscription_payments')
    _drop_index(op.f('ix_subscription_payments_subscription_id'), 'subscription_payments')
    _drop_index(op.f('ix_subscription_payments_plan_id'), 'subscription_payments')
    _drop_index(op.f('ix_subscription_payments_user_id'), 'subscription_payments')
    _drop_index(op.f('ix_subscription_payments_school_id'), 'subscription_payments')
    _drop_index(op.f('ix_subscription_payments_id'), 'subscription_payments')

    _drop_index('ix_subscriptions_status_end', 'subscriptions')
    _drop_index('ix_subscriptions_school_status', 'subscriptions')
    _drop_index('ix_subscriptions_user_status', 'subscriptions')
    _drop_index(op.f('ix_subscriptions_end_at'), 'subscriptions')
    _drop_index(op.f('ix_subscriptions_status'), 'subscriptions')
    _drop_index(op.f('ix_subscriptions_plan_id'), 'subscriptions')
    _drop_index(op.f('ix_subscriptions_user_id'), 'subscriptions')
    _drop_index(op.f('ix_subscriptions_school_id'), 'subscriptions')
    _drop_index(op.f('ix_subscriptions_id'), 'subscriptions')

    _drop_index('uq_user_subscription_override_type', 'user_subscription_overrides')
    _drop_index(op.f('ix_user_subscription_overrides_user_id'), 'user_subscription_overrides')
    _drop_index(op.f('ix_user_subscription_overrides_school_id'), 'user_subscription_overrides')
    _drop_index(op.f('ix_user_subscription_overrides_id'), 'user_subscription_overrides')

    _drop_index(op.f('ix_school_subscription_settings_school_id'), 'school_subscription_settings')
    _drop_index(op.f('ix_school_subscription_settings_id'), 'school_subscription_settings')

    _drop_index('ix_subscription_plans_school_role', 'subscription_plans')
    _drop_index('ix_subscription_plans_school_active', 'subscription_plans')
    _drop_index(op.f('ix_subscription_plans_role'), 'subscription_plans')
    _drop_index(op.f('ix_subscription_plans_school_id'), 'subscription_plans')
    _drop_index(op.f('ix_subscription_plans_id'), 'subscription_plans')
