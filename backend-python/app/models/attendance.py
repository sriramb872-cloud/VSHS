# backend-python/app/models/attendance.py
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Enum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class Attendance(Base):
    __tablename__ = "attendance_records"

    id = Column("attendance_id", Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    # Keep in sync with `app.models.attendance_record.AttendanceStatus`, which is
    # the enum the request schemas validate against.
    status = Column(Enum("PRESENT", "ABSENT", "LATE", "LEAVE", "VOID", name="attendance_status"), nullable=False)
    recorded_by = Column(Integer, nullable=True)
    remarks = Column(String(255), nullable=True)
    # Denormalised from the student's enrollment for the attendance date.
    # Nullable only for legacy rows that could not be backfilled; new writes
    # always set it (see app/services/attendance.py).
    academic_year_id = Column(
        Integer,
        ForeignKey("academic_years.academic_year_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    student = relationship("Student", back_populates="attendance_records")
    section = relationship("Section", back_populates="attendance_records")
    academic_year = relationship("AcademicYear")

    __table_args__ = (
        UniqueConstraint("student_id", "date", name="uq_student_attendance_date"),
        Index("idx_attendance_year_section_date", "academic_year_id", "section_id", "date"),
    )
