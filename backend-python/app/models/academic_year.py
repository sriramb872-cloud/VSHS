# backend-python/app/models/academic_year.py
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id = Column("academic_year_id", Integer, primary_key=True, index=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column("year_name", String(20), nullable=False)  # e.g. "2025-2026"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column("is_current", Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    school = relationship("School", back_populates="academic_years")
    enrollments = relationship("StudentEnrollment", back_populates="academic_year", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="academic_year", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="academic_year", cascade="all, delete-orphan")

    report_cards = relationship("ReportCard", back_populates="academic_year", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("school_id", "year_name", name="uq_school_academic_year"),
    )
