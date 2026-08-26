# backend-python/app/models/notification.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(
    "notification_id",
    Integer,
    primary_key=True,
    index=True,
    autoincrement=True
)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=True, index=True)
    sender_id = Column(
    "sender_user_id",
    Integer,
    ForeignKey("users.user_id", ondelete="SET NULL"),
    nullable=True,
    index=True
)
    sender_role = Column(String(50), nullable=True)  # PRINCIPAL, TEACHER, SUPER_ADMIN
    notification_type = Column(String(50), nullable=False)  # PUBLIC, STAFF_ONLY, CLASS_ONLY, ONLY_FOR_CLASS, ONLY_FOR_STUDENT
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    target_class_id = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=True, index=True)
    target_student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True, index=True)
    category = Column(String(50), nullable=True)  # PUBLIC, CLASS, CLASS_TEACHER, STAFF
    is_read = Column(Boolean, default=False, nullable=False)
    reference_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    sender = relationship("User", foreign_keys=[sender_id])
    target_class = relationship("Section", foreign_keys=[target_class_id])
    target_student = relationship("Student", foreign_keys=[target_student_id])
    school = relationship("School", foreign_keys=[school_id])


NotificationModel = Notification
