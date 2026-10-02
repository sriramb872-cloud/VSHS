# backend-python/app/models/user_subscription_override.py
"""Per-user subscription overrides (auditable manual decisions).

Example: "Student A is FREE until 31 Dec 2026 (scholarship)".

At most one row per (user, override_type) - enforced by a unique index - so
"the current override" is unambiguous. Every change (grant/update/remove) is
recorded in ``subscription_audit_logs`` with old/new values and a reason, so
history is preserved even though the override row itself is upserted.

``override_type`` is a String (not an ENUM) so new override kinds can be
added without a schema change.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String

from app.core.database import Base

# Currently supported override types. FREE = the user gets access without an
# active subscription until ``free_until`` (NULL = indefinitely).
OVERRIDE_TYPES = ("FREE",)


class UserSubscriptionOverride(Base):
    __tablename__ = "user_subscription_overrides"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    school_id = Column(
        Integer,
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    override_type = Column(String(30), nullable=False, default="FREE", server_default="FREE")

    # For FREE: the instant access stops. NULL = no end date (indefinite).
    free_until = Column(DateTime, nullable=True)

    reason = Column(String(500), nullable=True)

    # Who granted it (Super Admin). SET NULL keeps the override auditable if
    # the admin account is ever removed.
    created_by = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        # One current override of each type per user (upsert semantics).
        Index(
            "uq_user_subscription_override_type",
            "user_id",
            "override_type",
            unique=True,
        ),
    )
