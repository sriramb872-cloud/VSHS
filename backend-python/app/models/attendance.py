# backend-python/app/models/attendance.py
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Attendance(Base):
    __tablename__ = "attendance_records"

    id = Column("attendance_id", Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    status = Column(Enum("PRESENT", "ABSENT", "LATE", "LEAVE", name="attendance_status"), nullable=False)
    recorded_by = Column(Integer, nullable=True)

    student = relationship("Student", back_populates="attendance_records")
    section = relationship("Section", back_populates="attendance_records")

    __table_args__ = (
        UniqueConstraint("student_id", "date", name="uq_student_attendance_date"),
    )
