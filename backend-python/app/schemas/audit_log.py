"""
SCHOLARIS ERP - Audit Log Schemas
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AuditLogBase(BaseModel):
    action: str = Field(..., max_length=100)
    resource_type: str = Field(..., max_length=100)
    resource_id: Optional[str] = Field(None, max_length=100)
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = Field(None, max_length=45)


class AuditLogCreate(AuditLogBase):
    user_id: Optional[int] = None
    school_id: Optional[int] = None


class AuditLogResponse(AuditLogBase):
    id: int
    user_id: Optional[int] = None
    school_id: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True
