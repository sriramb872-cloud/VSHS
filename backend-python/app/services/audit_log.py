"""
SCHOLARIS ERP - Audit Log Service
"""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.audit_log import AuditLogRepository
from app.schemas.audit_log import AuditLogCreate, AuditLogResponse


class AuditLogService:
    def __init__(self, db: Session):
        self.repo = AuditLogRepository(db)

    def get_by_id(self, log_id: int) -> AuditLogResponse:
        log = self.repo.get_by_id(log_id)
        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log entry not found")
        return AuditLogResponse.model_validate(log)

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[AuditLogResponse]:
        logs = self.repo.get_by_school(school_id, skip, limit)
        return [AuditLogResponse.model_validate(l) for l in logs]

    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[AuditLogResponse]:
        logs = self.repo.get_by_user(user_id, skip, limit)
        return [AuditLogResponse.model_validate(l) for l in logs]

    def create_log(self, obj_in: AuditLogCreate) -> AuditLogResponse:
        log = self.repo.log(obj_in)
        return AuditLogResponse.model_validate(log)
