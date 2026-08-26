"""
SCHOLARIS ERP - Audit Log CRUD
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate


class CRUDAuditLog:
    def get(self, db: Session, log_id: int) -> Optional[AuditLog]:
        return db.query(AuditLog).filter(AuditLog.id == log_id).first()

    def get_multi_by_school(
        self, db: Session, school_id: int, skip: int = 0, limit: int = 100
    ) -> List[AuditLog]:
        return db.query(AuditLog).filter(
            AuditLog.school_id == school_id
        ).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

    def get_multi_by_user(
        self, db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[AuditLog]:
        return db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: AuditLogCreate) -> AuditLog:
        db_obj = AuditLog(
            user_id=obj_in.user_id,
            school_id=obj_in.school_id,
            action=obj_in.action,
            resource_type=obj_in.resource_type,
            resource_id=obj_in.resource_id,
            details=obj_in.details,
            ip_address=obj_in.ip_address
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


crud_audit_log = CRUDAuditLog()
