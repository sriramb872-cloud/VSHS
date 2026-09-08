# backend-python/app/models/notification_read.py
# Maps to the EXISTING `user_notifications` table already in your database
# — not a new table.
from sqlalchemy import Column, Integer, BigInteger, Boolean, DateTime, ForeignKey
from app.core.database import Base


class NotificationRead(Base):
    __tablename__ = "user_notifications"

    id = Column("user_notification_id", BigInteger, primary_key=True, index=True, autoincrement=True)
    notification_id = Column(
        Integer,
        ForeignKey("notifications.notification_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_read = Column(Boolean, default=False, nullable=True)
    read_at = Column(DateTime, nullable=True)


NotificationReadModel = NotificationRead
