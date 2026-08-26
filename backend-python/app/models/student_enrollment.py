from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Date,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"

    id = Column("enrollment_id", Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(
        Integer,
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    academic_year_id = Column(
        Integer,
        ForeignKey("academic_years.academic_year_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section_id = Column(
        Integer,
        ForeignKey("sections.section_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    roll_number = Column(
        String(20),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    student = relationship(
        "Student",
        back_populates="enrollments",
    )

    academic_year = relationship(
        "AcademicYear",
        back_populates="enrollments",
    )

    section = relationship(
        "Section",
        back_populates="enrollments",
    )

    __table_args__ = (
        UniqueConstraint("academic_year_id", "section_id", "roll_number", name="uq_academic_section_roll"),
    )
