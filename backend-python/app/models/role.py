"""
SCHOLARIS ERP - Role Model / Enumeration
"""

import enum
from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from app.core.database import Base


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    PRINCIPAL = "PRINCIPAL"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(SQLEnum(UserRole), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
