from datetime import datetime, time
from sqlalchemy import Column, Integer, String, BigInteger, Time, DateTime, ForeignKey
from sqlalchemy.orm import relationship, synonym
from app.core.database import Base


class Timetable(Base):
    __tablename__ = "timetables"

    id = Column("timetable_id", BigInteger, primary_key=True, index=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.academic_year_id", ondelete="CASCADE"), nullable=False, index=True)
    grade_id = Column(Integer, ForeignKey("grades.grade_id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(BigInteger, ForeignKey("teachers.teacher_id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(String(20), nullable=False)  # MONDAY, TUESDAY, etc.
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    room_number = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    timetable_id = synonym("id")

    school = relationship("School", back_populates="timetables")
    academic_year = relationship("AcademicYear", back_populates="timetables")
    grade = relationship("Grade", back_populates="timetables")
    section = relationship("Section", back_populates="timetables")
    subject = relationship("Subject", back_populates="timetables")
    teacher = relationship("Teacher", back_populates="timetables")


TimetableModel = Timetable
TimetableEntryModel = Timetable



