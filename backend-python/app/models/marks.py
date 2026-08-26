"""
SCHOLARIS ERP - Marks Model
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint, Index, CheckConstraint, func
from app.core.database import Base


class Marks(Base):
    __tablename__ = "marks"

    id = Column(Integer, primary_key=True, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    marks_obtained = Column(Float, nullable=False)
    max_marks = Column(Float, nullable=False, default=100.0)
    remarks = Column(String(255), nullable=True)
    entered_by_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("examination_id", "student_id", "subject_id", name="uq_exam_student_subject_marks"),
        CheckConstraint("marks_obtained >= 0", name="chk_marks_obtained_positive"),
        CheckConstraint("marks_obtained <= max_marks", name="chk_marks_obtained_lte_max"),
        Index("idx_marks_student_exam", "student_id", "examination_id"),
        Index("idx_marks_school_exam", "school_id", "examination_id"),
    )
