# backend-python/app/models/subject.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column("subject_id", Integer, primary_key=True, index=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column("subject_name", String(100), nullable=False)  # e.g. "Mathematics"
    code = Column("subject_code", String(30), nullable=True)
    is_optional = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    school = relationship("School", back_populates="subjects")
    grade_subjects = relationship("GradeSubject", back_populates="subject", cascade="all, delete-orphan")
    homeworks = relationship("Homework", back_populates="subject", cascade="all, delete-orphan")
    exam_results = relationship("ExamResult", back_populates="subject", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="subject", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("school_id", "subject_name", name="uq_school_subject_name"),
    )
