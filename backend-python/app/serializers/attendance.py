"""
SCHOLARIS ERP - Attendance Serializer
"""

from typing import Any, Dict, List

from app.models.attendance_record import AttendanceRecord


def _status_value(record: AttendanceRecord) -> str:
    status = record.status
    return getattr(status, "value", None) or str(status)


def serialize_attendance_record(record: AttendanceRecord) -> Dict[str, Any]:
    """Serialize an ``attendance_records`` row.

    Only real columns are read. This previously read ``school_id``,
    ``recorded_by_id``, ``created_at`` and ``updated_at``, none of which exist
    on the ``Attendance`` model, so calling it raised ``AttributeError``.
    """
    return {
        "id": record.id,
        "student_id": record.student_id,
        "section_id": record.section_id,
        "date": record.date.isoformat() if record.date else None,
        "status": _status_value(record),
        "remarks": record.remarks,
        "recorded_by": record.recorded_by,
    }


def serialize_attendance_records(records: List[AttendanceRecord]) -> List[Dict[str, Any]]:
    return [serialize_attendance_record(r) for r in records]
