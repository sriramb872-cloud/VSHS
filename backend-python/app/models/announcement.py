# backend-python/app/models/announcement.py
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from typing import Optional


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    target_role = Column(String(50), nullable=True)  # ALL, TEACHER, STUDENT, etc.
    priority = Column(String(50), default="Normal", nullable=True)
    academic_year_id = Column(Integer, nullable=True)
    grade_id = Column(Integer, nullable=True)
    section_id = Column(Integer, nullable=True)
    publish_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expiry_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def description(self) -> str:
        return self.content

    @description.setter
    def description(self, val: str):
        self.content = val

    @property
    def author_id(self) -> Optional[int]:
        return self.created_by

    @author_id.setter
    def author_id(self, val: Optional[int]):
        self.created_by = val

    @property
    def audience(self) -> str:
        return self.target_role or "School-Wide"

    @audience.setter
    def audience(self, val):
        self.target_role = str(val.value if hasattr(val, "value") else val)

    @property
    def status(self) -> str:
        return "Published" if self.is_active else "Draft"

    @status.setter
    def status(self, val):
        val_str = str(val.value if hasattr(val, "value") else val)
        self.is_active = (val_str == "Published")

    school = relationship("School", back_populates="announcements")
    creator = relationship("User", foreign_keys=[created_by])


AnnouncementModel = Announcement

