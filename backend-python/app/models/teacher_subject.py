"""
SCHOLARIS ERP - Teacher Subject Assignment Model
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, Index, func
from app.core.database import Base


class TeacherSubject(Base):
    __tablename__ = "teacher_subjects"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.teacher_id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True)
    grade_id = Column(Integer, ForeignKey("grades.grade_id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "subject_id", "grade_id", "section_id", "school_id",
            name="uq_teacher_subject_grade_section_school"
        ),
        Index("idx_teacher_assignments", "teacher_id", "school_id"),
        Index("idx_class_subject_assignment", "grade_id", "section_id", "subject_id"),
    )
