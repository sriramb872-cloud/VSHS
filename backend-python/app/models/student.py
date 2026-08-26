from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column("student_id", Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    school_id = Column(
        Integer,
        ForeignKey("schools.school_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    admission_number = Column(
        String(30),
        nullable=True,
    )

    roll_number = Column(
        String(50),
        nullable=True,
    )

    admission_date = Column(
        Date,
        nullable=True,
    )

    date_of_birth = Column(
        Date,
        nullable=True,
    )

    gender = Column(
        String(20),
        nullable=True,
    )

    blood_group = Column(
        String(10),
        nullable=True,
    )

    father_name = Column(
        String(100),
        nullable=True,
    )

    father_mobile = Column(
        String(15),
        nullable=True,
    )

    mother_name = Column(
        String(100),
        nullable=True,
    )

    mother_mobile = Column(
        String(15),
        nullable=True,
    )

    guardian_mobile = Column(
        String(15),
        nullable=True,
    )

    address = Column(
        String(500),
        nullable=True,
    )

    student_status = Column(
        String(20),
        default="ACTIVE",
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="student_profile",
        foreign_keys=[user_id]
    )

    school = relationship(
        "School",
        back_populates="students",
    )

    enrollments = relationship(
        "StudentEnrollment",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    attendance_records = relationship(
        "Attendance",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    exam_results = relationship(
        "ExamResult",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    report_cards = relationship(
        "ReportCard",
        back_populates="student",
        cascade="all, delete-orphan",
    )


StudentModel = Student
