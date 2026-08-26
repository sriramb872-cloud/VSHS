# app/services/dashboard.py
from datetime import date, datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.crud.dashboard import dashboard as crud_dashboard
from app.models.user import User
from app.models.teacher import Teacher
from app.models.timetable import Timetable
from app.models.section import Section
from app.models.attendance import Attendance
from app.models.homework import Homework
from app.models.announcement import Announcement
from app.services.timetable import serialize_timetable
from app.schemas.dashboard import (
    SuperAdminDashboardResponse,
    PrincipalDashboardResponse,
    TeacherDashboardResponse,
    StudentDashboardResponse,
    ParentDashboardResponse,
)

class DashboardService:
    @staticmethod
    def get_super_admin_dashboard(db: Session, current_user: User) -> SuperAdminDashboardResponse:
        if str(current_user.role).upper() != "SUPER_ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        stats = crud_dashboard.get_super_admin_stats(db)
        return SuperAdminDashboardResponse(
            total_schools=stats["total_schools"],
            total_principals=stats["total_principals"],
            total_teachers=stats["total_teachers"],
            total_students=stats["total_students"],
            active_schools=stats["active_schools"],
            recent_activity=[],
            system_health="Healthy",
            storage_usage="45%"
        )

    @staticmethod
    def get_principal_dashboard(db: Session, current_user: User) -> PrincipalDashboardResponse:
        school_id = getattr(current_user, "school_id", None)
        stats = crud_dashboard.get_principal_stats(db, school_id=school_id)
        return PrincipalDashboardResponse(
            total_teachers=stats.get("total_teachers", 0),
            total_students=stats.get("total_students", 0),
            todays_attendance=stats.get("todays_attendance", {}),
            upcoming_exams=stats.get("upcoming_exams", []),
            recent_homework=stats.get("recent_homework", []),
            announcements=stats.get("announcements", []),
            calendar_events=stats.get("calendar_events", [])
        )

    @staticmethod
    def get_teacher_dashboard(db: Session, current_user: User) -> TeacherDashboardResponse:
        teacher = getattr(current_user, "teacher_profile", None) or (
            db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        )
        if not teacher:
            return TeacherDashboardResponse(
                todays_timetable=[],
                attendance_pending=False,
                homework_summary=[],
                upcoming_exams=[],
                announcements=[],
                calendar_events=[]
            )

        school_id = current_user.school_id or teacher.school_id
        today_day = datetime.utcnow().strftime("%A")

        # Today's timetable for this teacher
        todays_slots = db.query(Timetable).filter(
            Timetable.teacher_id == teacher.id,
            func.lower(Timetable.day_of_week) == today_day.lower()
        )
        if school_id:
            todays_slots = todays_slots.filter(Timetable.school_id == school_id)
        todays_slots = todays_slots.order_by(Timetable.start_time.asc()).all()

        serialized_timetable = [serialize_timetable(slot) for slot in todays_slots]

        # Check attendance pending for class teacher section
        class_section = db.query(Section).filter(Section.class_teacher_id == teacher.id)
        if school_id:
            class_section = class_section.filter(Section.school_id == school_id)
        class_section = class_section.first()

        attendance_pending = False
        if class_section:
            today_date = date.today()
            recorded_count = db.query(Attendance).filter(
                Attendance.section_id == class_section.id,
                Attendance.date == today_date
            ).count()
            attendance_pending = (recorded_count == 0)

        # Homework summary for this teacher
        hw_query = db.query(Homework).filter(Homework.teacher_id == teacher.id)
        if school_id:
            hw_query = hw_query.filter(Homework.school_id == school_id)
        homework_list = hw_query.order_by(Homework.due_date.desc()).limit(10).all()

        serialized_homework = [
            {
                "id": hw.id,
                "title": hw.title,
                "description": hw.description,
                "grade_id": hw.grade_id,
                "section_id": hw.section_id,
                "subject_id": hw.subject_id,
                "due_date": str(hw.due_date),
                "created_at": str(hw.created_at) if hw.created_at else None,
            }
            for hw in homework_list
        ]

        # Recent announcements
        ann_query = db.query(Announcement)
        if school_id:
            ann_query = ann_query.filter(Announcement.school_id == school_id)
        announcements = ann_query.order_by(Announcement.created_at.desc()).limit(5).all()

        serialized_announcements = [
            {
                "id": a.id,
                "title": getattr(a, "title", ""),
                "description": getattr(a, "content", "") or getattr(a, "title", ""),
                "created_at": str(a.created_at) if getattr(a, "created_at", None) else None,
            }
            for a in announcements
        ]

        return TeacherDashboardResponse(
            todays_timetable=serialized_timetable,
            attendance_pending=attendance_pending,
            homework_summary=serialized_homework,
            upcoming_exams=[],
            announcements=serialized_announcements,
            calendar_events=[]
        )

    @staticmethod
    def get_student_dashboard(db: Session, current_user: User) -> StudentDashboardResponse:
        return StudentDashboardResponse(
            todays_timetable=[],
            attendance_percentage=96.5,
            pending_homework=[],
            upcoming_exams=[],
            latest_marks=[],
            report_card_summary=None,
            announcements=[],
            calendar_events=[]
        )

    @staticmethod
    def get_parent_dashboard(db: Session, current_user: User) -> ParentDashboardResponse:
        return ParentDashboardResponse(
            child_attendance={"present": 48, "total": 50},
            homework=[],
            upcoming_exams=[],
            latest_report_card=None,
            announcements=[],
            calendar_events=[],
            fee_summary={"status": "Paid", "due": 0.0},
            teacher_messages=[]
        )

    """
SCHOLARIS ERP

Module:
Description:

TODO:
"""
