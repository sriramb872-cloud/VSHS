from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column("user_id", Integer, primary_key=True, index=True, autoincrement=True)
    school_id = Column(
        Integer,
        ForeignKey("schools.school_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    mobile = Column("mobile_number", String(15), index=True, nullable=False)

    email = Column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    display_name = Column("full_name", String(100), nullable=False)

    profile_photo = Column(String(255), nullable=True)

    role = Column(
        Enum(
            "SUPER_ADMIN",
            "PRINCIPAL",
            "TEACHER",
            "STUDENT",
        ),
        nullable=False,
        index=True,
    )

    is_active = Column("account_status", String(50), default="ACTIVE", nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=True,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=True,
    )

    school = relationship(
        "School",
        back_populates="users",
    )

    principal_profile = relationship(
        "Principal",
        back_populates="user",
        uselist=False,
        foreign_keys="Principal.user_id"
    )

    teacher_profile = relationship(
        "Teacher",
        back_populates="user",
        uselist=False,
        foreign_keys="Teacher.user_id"
    )

    student_profile = relationship(
        "Student",
        back_populates="user",
        uselist=False,
        foreign_keys="Student.user_id"
    )


UserModel = User
