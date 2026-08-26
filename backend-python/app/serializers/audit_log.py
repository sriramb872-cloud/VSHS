"""
SCHOLARIS ERP - Audit Log Serializer
"""

from typing import Any, Dict
from app.models.audit_log import AuditLog


def serialize_audit_log(log: AuditLog) -> Dict[str, Any]:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "school_id": log.school_id,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "details": log.details,
        "ip_address": log.ip_address,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    }
