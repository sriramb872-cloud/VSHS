# backend-python/app/models/principal.py
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, BigInteger, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Principal(Base):
    __tablename__ = "principal_profiles"

    id = Column("principal_id", BigInteger, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.school_id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(String(30), nullable=True)
    joining_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="principal_profile", foreign_keys=[user_id])
    school = relationship("School", back_populates="principals")


PrincipalModel = Principal
