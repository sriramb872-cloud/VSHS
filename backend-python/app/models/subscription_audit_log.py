# backend-python/app/models/subscription_audit_log.py
"""Audit trail for every Super Admin action that affects billing or access.

Distinct from the generic ``audit_logs`` table: these rows carry the
before/after *values* of a subscription decision (e.g. old ``₹3/month``,
new ``FREE until 2026-12-31``, reason ``Scholarship``) and are exposed
read-only through the subscription API.

Actions (non-exhaustive, stored as strings so new actions need no migration):
    SCHOOL_SUBSCRIPTIONS_ENABLED / SCHOOL_SUBSCRIPTIONS_DISABLED
    SCHOOL_FREE_GRANTED / SCHOOL_FREE_REMOVED
    PLAN_CREATED / PLAN_UPDATED / PLAN_DEACTIVATED
    USER_FREE_GRANTED / USER_FREE_REMOVED
    USER_SUBSCRIPTION_GRANTED / USER_SUBSCRIPTION_EXTENDED
    USER_SUBSCRIPTION_CANCELLED / USER_SUBSCRIPTION_SUSPENDED
    USER_SUBSCRIPTION_RESTORED
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.core.database import Base


class SubscriptionAuditLog(Base):
    __tablename__ = "subscription_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    school_id = Column(
        Integer,
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # The user the decision was ABOUT (nullable for school-level actions).
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # The Super Admin who MADE the decision. SET NULL keeps the audit row if
    # the admin account disappears.
    admin_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action = Column(String(60), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(String(500), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        # "History for this school / this user" pages.
        Index("ix_subscription_audit_school_action", "school_id", "action"),
        Index("ix_subscription_audit_user_created", "user_id", "created_at"),
    )
