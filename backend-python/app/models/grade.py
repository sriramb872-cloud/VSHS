# backend-python/app/models/grade.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Grade(Base):
    __tablename__ = "grades"

    id = Column("grade_id", Integer, primary_key=True, index=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column("grade_name", String(30), nullable=False)  # e.g. "Grade 10"
    display_order = Column("grade_order", Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    school = relationship("School", back_populates="grades")
    sections = relationship("Section", back_populates="grade", cascade="all, delete-orphan")
    grade_subjects = relationship("GradeSubject", back_populates="grade", cascade="all, delete-orphan")
    homeworks = relationship("Homework", back_populates="grade", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="grade", cascade="all, delete-orphan")


    __table_args__ = (
        UniqueConstraint("school_id", "grade_name", name="uq_school_grade_name"),
    )
