# backend-python/app/models/app_settings.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, default=1)
    platform_name = Column(String(255), default="Scholaris ERP", nullable=False)
    platform_logo = Column(String(500), default="", nullable=True)
    default_language = Column(String(10), default="en", nullable=False)
    time_zone = Column(String(50), default="UTC", nullable=False)
    maintenance_mode = Column(Boolean, default=False, nullable=False)
    email_configuration = Column(JSON, default=dict, nullable=True)
    backup_settings = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SchoolSettings(Base):
    __tablename__ = "school_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    school_name = Column(String(255), nullable=True)
    school_logo = Column(String(500), default="", nullable=True)
    school_address = Column(String(500), default="", nullable=True)
    phone_number = Column(String(50), default="", nullable=True)
    email = Column(String(100), default="", nullable=True)
    academic_year = Column(String(50), default="", nullable=True)
    school_working_days = Column(JSON, default=list, nullable=True)
    school_timings = Column(String(100), default="", nullable=True)
    grade_settings = Column(JSON, default=dict, nullable=True)
    section_settings = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    school = relationship("School")


class UserAppSettings(Base):
    __tablename__ = "user_app_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    profile_information = Column(JSON, default=dict, nullable=True)
    notification_preferences = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")
