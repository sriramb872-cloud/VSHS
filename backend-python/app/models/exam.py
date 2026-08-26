from datetime import datetime, date, time
from sqlalchemy import Column, Integer, Float, String, Date, Time, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.academic_year_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # e.g. "FA1", "SA1"
    exam_type = Column(String(100), nullable=False)  # FORMATIVE, SUMMATIVE, Unit Test, etc.
    grade_id = Column(Integer, nullable=True, default=1)
    section_id = Column(Integer, nullable=True, default=1)
    subject_id = Column(Integer, nullable=True, default=1)
    teacher_id = Column(Integer, nullable=True, default=1)
    exam_date = Column(Date, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    start_time = Column(Time, nullable=True, default=time(9, 0))
    end_time = Column(Time, nullable=True, default=time(12, 0))
    maximum_marks = Column(Float, default=100.0, nullable=True)
    passing_marks = Column(Float, default=35.0, nullable=True)
    instructions = Column(String(500), nullable=True)
    status = Column(String(50), default="SCHEDULED", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    school = relationship("School", back_populates="exams")
    academic_year = relationship("AcademicYear", back_populates="exams")
    exam_results = relationship("ExamResult", back_populates="exam", cascade="all, delete-orphan")


ExamModel = Exam

