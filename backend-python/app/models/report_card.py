# backend-python/app/models/report_card.py
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class ReportCard(Base):
    __tablename__ = "report_cards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.academic_year_id", ondelete="CASCADE"), nullable=False, index=True)
    term_name = Column(String(100), nullable=False)  # e.g. "Term 1", "Term 2", "Annual"
    total_marks = Column(Float, default=0.0, nullable=False)
    percentage = Column(Float, default=0.0, nullable=False)
    grade_letter = Column(String(10), nullable=True)
    remarks = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="report_cards")
    academic_year = relationship("AcademicYear", back_populates="report_cards")

    __table_args__ = (
        UniqueConstraint("student_id", "academic_year_id", "term_name", name="uq_student_term_report_card"),
    )


ReportCardModel = ReportCard

