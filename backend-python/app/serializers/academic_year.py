"""
SCHOLARIS ERP - Academic Year Serializer
"""

from typing import Any, Dict
from app.models.academic_year import AcademicYear


def serialize_academic_year(academic_year: AcademicYear) -> Dict[str, Any]:
    return {
        "id": academic_year.id,
        "name": academic_year.name,
        "start_date": academic_year.start_date.isoformat() if academic_year.start_date else None,
        "end_date": academic_year.end_date.isoformat() if academic_year.end_date else None,
        "is_active": academic_year.is_active,
        "school_id": academic_year.school_id,
        "created_at": academic_year.created_at.isoformat() if academic_year.created_at else None,
        "updated_at": academic_year.updated_at.isoformat() if academic_year.updated_at else None,
    }
