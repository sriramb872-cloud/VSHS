# app/schemas/dashboard.py
from typing import List, Optional, Any
from pydantic import BaseModel

class SuperAdminDashboardResponse(BaseModel):
    total_schools: int
    total_principals: int
    total_teachers: int
    total_students: int
    active_schools: int
    recent_activity: List[Any] = []
    system_health: str = "Healthy"
    storage_usage: str = "45%"

    class Config:
        from_attributes = True

class PrincipalDashboardResponse(BaseModel):
    total_teachers: int
    total_students: int
    todays_attendance: dict = {}
    upcoming_exams: List[Any] = []
    recent_homework: List[Any] = []
    announcements: List[Any] = []
    calendar_events: List[Any] = []

    class Config:
        from_attributes = True

class TeacherDashboardResponse(BaseModel):
    todays_timetable: List[Any] = []
    attendance_pending: bool = False
    homework_summary: List[Any] = []
    upcoming_exams: List[Any] = []
    announcements: List[Any] = []
    calendar_events: List[Any] = []

    class Config:
        from_attributes = True

class StudentDashboardResponse(BaseModel):
    todays_timetable: List[Any] = []
    attendance_percentage: float = 0.0
    pending_homework: List[Any] = []
    upcoming_exams: List[Any] = []
    latest_marks: List[Any] = []
    report_card_summary: Optional[Any] = None
    announcements: List[Any] = []
    calendar_events: List[Any] = []

    class Config:
        from_attributes = True

class ParentDashboardResponse(BaseModel):
    child_attendance: dict = {}
    homework: List[Any] = []
    upcoming_exams: List[Any] = []
    latest_report_card: Optional[Any] = None
    announcements: List[Any] = []
    calendar_events: List[Any] = []
    fee_summary: dict = {"status": "Paid", "due": 0.0}
    teacher_messages: List[Any] = []

    class Config:
        from_attributes = True
        """
SCHOLARIS ERP

Module:
Description:

TODO:
"""
