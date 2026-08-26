# backend-python/app/models/teacher.py
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column("teacher_id", BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    qualification = Column(String(100), nullable=True)
    joining_date = Column(Date, nullable=True)
    address = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="teacher_profile", foreign_keys=[user_id])
    school = relationship("School", back_populates="teachers")
    grade_subjects = relationship("GradeSubject", back_populates="teacher")
    homeworks = relationship("Homework", back_populates="teacher", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="teacher", cascade="all, delete-orphan")



TeacherModel = Teacher
