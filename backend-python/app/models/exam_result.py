# backend-python/app/models/exam_result.py
from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class ExamResult(Base):
    __tablename__ = "exam_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Component marks (Max: written_test=20, project=5, read_reflection=5, notebook=5 -> Total Raw = 40)
    written_test = Column(Float, default=0.0, nullable=False)
    project = Column(Float, default=0.0, nullable=False)
    read_reflection = Column(Float, default=0.0, nullable=False)
    notebook = Column(Float, default=0.0, nullable=False)

    @property
    def marks_obtained(self) -> float:
        return self.written_test

    @marks_obtained.setter
    def marks_obtained(self, value: float):
        self.written_test = value

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    exam = relationship("Exam", back_populates="exam_results")
    student = relationship("Student", back_populates="exam_results")
    subject = relationship("Subject", back_populates="exam_results")

    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", "subject_id", name="uq_exam_student_subject_result"),
    )
