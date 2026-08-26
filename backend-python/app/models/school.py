# backend-python/app/models/school.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class School(Base):
    __tablename__ = "schools"

    id = Column("school_id", Integer, primary_key=True, index=True, autoincrement=True)
    name = Column("school_name", String(150), nullable=False)
    code = Column("school_code", String(30), unique=True, index=True, nullable=True)
    contact_email = Column("email", String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    users = relationship("User", back_populates="school", cascade="all, delete-orphan")
    academic_years = relationship("AcademicYear", back_populates="school", cascade="all, delete-orphan")
    grades = relationship("Grade", back_populates="school", cascade="all, delete-orphan")
    subjects = relationship("Subject", back_populates="school", cascade="all, delete-orphan")
    principals = relationship("Principal", back_populates="school", cascade="all, delete-orphan")
    teachers = relationship("Teacher", back_populates="school", cascade="all, delete-orphan")
    students = relationship("Student", back_populates="school", cascade="all, delete-orphan")
    homeworks = relationship("Homework", back_populates="school", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="school", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="school", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="school", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="school", cascade="all, delete-orphan")
    sections = relationship("Section", back_populates="school")

SchoolModel = School

