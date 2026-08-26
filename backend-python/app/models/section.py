# backend-python/app/models/section.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Section(Base):
    __tablename__ = "sections"

    id = Column("section_id", Integer, primary_key=True, index=True, autoincrement=True)
    grade_id = Column(Integer, ForeignKey("grades.grade_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column("section_name", String(10), nullable=False)  # e.g. "10-A"
    class_teacher_id = Column(Integer, ForeignKey("teachers.teacher_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    school_id = Column(Integer,ForeignKey("schools.school_id"),nullable=False,index=True)

    grade = relationship("Grade", back_populates="sections")
    class_teacher = relationship("Teacher", foreign_keys=[class_teacher_id])
    enrollments = relationship("StudentEnrollment", back_populates="section", cascade="all, delete-orphan")
    homeworks = relationship("Homework", back_populates="section", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="section", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="section", cascade="all, delete-orphan")
    school = relationship("School", back_populates="sections")

    __table_args__ = (
        UniqueConstraint("grade_id", "section_name", name="uq_grade_section_name"),
    )
