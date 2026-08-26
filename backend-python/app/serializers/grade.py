"""
SCHOLARIS ERP - Grade Serializer
"""

from typing import Any, Dict
from app.models.grade import Grade


def serialize_grade(grade: Grade) -> Dict[str, Any]:
    return {
        "id": grade.id,
        "name": grade.name,
        "code": grade.code,
        "description": grade.description,
        "school_id": grade.school_id,
        "created_at": grade.created_at.isoformat() if grade.created_at else None,
        "updated_at": grade.updated_at.isoformat() if grade.updated_at else None,
    }
