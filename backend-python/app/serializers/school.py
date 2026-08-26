"""
SCHOLARIS ERP - School Serializer
"""

from typing import Any, Dict
from app.models.school import School


def serialize_school(school: School) -> Dict[str, Any]:
    return {
        "id": school.id,
        "name": school.name,
        "code": school.code,
        "address": school.address,
        "phone": school.phone,
        "email": school.email,
        "website": school.website,
        "logo_url": school.logo_url,
        "is_active": school.is_active,
        "created_at": school.created_at.isoformat() if school.created_at else None,
        "updated_at": school.updated_at.isoformat() if school.updated_at else None,
    }
