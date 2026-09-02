# backend-python/app/models/marks.py
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Marks(Base):
    __tablename__ = "marks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_subject_id = Column(Integer, ForeignKey("exam_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    marks_obtained = Column(Float, nullable=False)
    max_marks = Column(Float, nullable=False, default=100.0)
    remarks = Column(String(255), nullable=True)
    entered_by_id = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    exam_subject = relationship("ExamSubject", back_populates="marks")
    student = relationship("Student")
    school = relationship("School")
    entered_by = relationship("User", foreign_keys=[entered_by_id])

    __table_args__ = (
        UniqueConstraint("exam_subject_id", "student_id", name="uq_exam_subject_student_marks"),
        CheckConstraint("marks_obtained >= 0", name="chk_marks_obtained_positive"),
        Index("idx_marks_student_exam_subject", "student_id", "exam_subject_id"),
        Index("idx_marks_school_exam_subject", "school_id", "exam_subject_id"),
    )


MarksModel = Marks
