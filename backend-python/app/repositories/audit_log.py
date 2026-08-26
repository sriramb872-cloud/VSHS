"""
SCHOLARIS ERP - Audit Log Repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.crud.audit_log import crud_audit_log
from app.schemas.audit_log import AuditLogCreate


class AuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, log_id: int) -> Optional[AuditLog]:
        return crud_audit_log.get(self.db, log_id)

    def get_by_school(self, school_id: int, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        return crud_audit_log.get_multi_by_school(self.db, school_id, skip, limit)

    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        return crud_audit_log.get_multi_by_user(self.db, user_id, skip, limit)

    def log(self, obj_in: AuditLogCreate) -> AuditLog:
        return crud_audit_log.create(self.db, obj_in)
