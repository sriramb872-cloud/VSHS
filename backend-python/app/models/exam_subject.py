# backend-python/app/models/exam_subject.py
from datetime import datetime
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class ExamSubject(Base):
    __tablename__ = "exam_subjects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.teacher_id", ondelete="SET NULL"), nullable=True, index=True)
    maximum_marks = Column(Float, default=100.0, nullable=False)
    passing_marks = Column(Float, default=35.0, nullable=False)
    is_marks_submitted = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    exam = relationship("Exam", back_populates="exam_subjects")
    subject = relationship("Subject")
    teacher = relationship("Teacher")
    marks = relationship("Marks", back_populates="exam_subject", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("exam_id", "subject_id", name="uq_exam_subject"),
    )


ExamSubjectModel = ExamSubject
