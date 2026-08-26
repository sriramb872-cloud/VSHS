"""
SCHOLARIS ERP - Attendance Serializer
"""

from typing import Any, Dict, List
from app.models.attendance_record import AttendanceRecord


def serialize_attendance_record(record: AttendanceRecord) -> Dict[str, Any]:
    return {
        "id": record.id,
        "student_id": record.student_id,
        "school_id": record.school_id,
        "date": record.date.isoformat() if record.date else None,
        "status": record.status.value if hasattr(record.status, 'value') else str(record.status),
        "remarks": record.remarks,
        "recorded_by_id": record.recorded_by_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def serialize_attendance_records(records: List[AttendanceRecord]) -> List[Dict[str, Any]]:
    return [serialize_attendance_record(r) for r in records]
