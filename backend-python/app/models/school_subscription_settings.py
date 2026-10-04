# backend-python/app/models/school_subscription_settings.py
"""Per-school subscription switches.

``subscriptions_enabled = False`` (the default, and the state implied when
no row exists at all) means the school does not require subscriptions -
every user keeps normal access. When enabled, normal role/user subscription
rules apply after any active school-wide free override.

``free_until`` makes the *entire school* free until that timestamp. Once the
timestamp passes, billing enforcement resumes automatically - no job needed,
the access check evaluates the clock.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer

from app.core.database import Base


class SchoolSubscriptionSettings(Base):
    __tablename__ = "school_subscription_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    school_id = Column(
        Integer,
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    subscriptions_enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    # School-wide free period. NULL = no school-wide free override.
    free_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
