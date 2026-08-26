# backend-python/app/models/grade_subject.py
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class GradeSubject(Base):
    __tablename__ = "grade_subjects"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    grade_id = Column(Integer, ForeignKey("grades.grade_id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(BigInteger, ForeignKey("teachers.teacher_id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    grade = relationship("Grade", back_populates="grade_subjects")
    subject = relationship("Subject", back_populates="grade_subjects")
    teacher = relationship("Teacher", back_populates="grade_subjects")

    __table_args__ = (
        UniqueConstraint("grade_id", "subject_id", name="uq_grade_subject"),
    )
    
