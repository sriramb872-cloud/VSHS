"""
SCHOLARIS ERP - Audit Log Validator
"""

from fastapi import HTTPException, status


def validate_audit_log_payload(action: str, resource_type: str) -> None:
    if not action or not action.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audit log action cannot be empty")
    if not resource_type or not resource_type.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audit log resource_type cannot be empty")
