"""
SCHOLARIS ERP - Attendance Record Model
"""

import enum
from app.models.attendance import Attendance

class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    LEAVE = "LEAVE"
    EXCUSED = "EXCUSED"

# Canonical ORM model for attendance_records table is Attendance
AttendanceRecord = Attendance
