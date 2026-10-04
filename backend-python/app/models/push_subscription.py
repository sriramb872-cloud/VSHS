# backend-python/app/models/push_subscription.py
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class PushSubscription(Base):
    """A browser's Web Push subscription, bound to one user account.

    ``endpoint`` is the push-service URL; it is stored in full for delivery
    but indexed through ``endpoint_hash`` (SHA-256) because MySQL cannot
    index a long TEXT column. ``endpoint_hash`` is UNIQUE so a shared school
    device (same endpoint, different logged-in user) upserts instead of
    duplicating.
    """

    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    endpoint = Column(Text, nullable=False)
    endpoint_hash = Column(String(64), nullable=False, unique=True, index=True)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    user_agent = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])


PushSubscriptionModel = PushSubscription
