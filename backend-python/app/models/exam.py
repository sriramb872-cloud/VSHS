# backend-python/app/models/exam.py
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.academic_year_id", ondelete="CASCADE"), nullable=False, index=True)
    grade_id = Column(Integer, ForeignKey("grades.grade_id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g. "FA1", "SA1"
    exam_type = Column(String(100), nullable=False)  # Formative Assessment, Summative Assessment, etc.
    assessment_mode = Column(
        Enum("FORMATIVE", "SUMMATIVE", name="exam_assessment_mode"),
        nullable=False,
        default="FORMATIVE",
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(
        Enum("SCHEDULED", "MARKS_IN_PROGRESS", "PUBLISHED", name="exam_status"),
        default="SCHEDULED",
        nullable=False,
    )
    created_by_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    school = relationship("School", back_populates="exams")
    academic_year = relationship("AcademicYear", back_populates="exams")
    grade = relationship("Grade")
    section = relationship("Section")
    created_by = relationship("User", foreign_keys=[created_by_id])
    exam_subjects = relationship("ExamSubject", back_populates="exam", cascade="all, delete-orphan")
    exam_results = relationship("ExamResult", back_populates="exam", cascade="all, delete-orphan")


ExamModel = Exam
