"""
SCHOLARIS ERP - Attendance Record Model
"""

import enum

from app.models.attendance import Attendance


class AttendanceStatus(str, enum.Enum):
    """Canonical attendance statuses.

    These must stay in sync with the ``attendance_records.status`` MySQL ENUM,
    which is declared in :mod:`app.models.attendance` as
    ``("PRESENT", "ABSENT", "LATE", "LEAVE", "VOID")``.

    This enum previously also declared ``EXCUSED``, which is *not* a member of
    the database ENUM. Because ``AttendanceCreate.status`` is typed with this
    enum, ``POST /attendance`` accepted ``"EXCUSED"`` and then failed at INSERT
    with a 500 (MySQL "Data truncated for column 'status'"). ``VOID`` was
    missing, so a voided record could never be re-created through the API even
    though the column allows it.
    """

    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    LEAVE = "LEAVE"
    VOID = "VOID"


# Canonical ORM model for attendance_records table is Attendance
AttendanceRecord = Attendance
