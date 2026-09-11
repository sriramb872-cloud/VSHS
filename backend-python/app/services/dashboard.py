# app/services/dashboard.py
from datetime import date
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.crud.dashboard import dashboard as crud_dashboard
from app.models.user import User
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.timetable import Timetable
from app.models.section import Section
from app.models.attendance import Attendance
from app.models.homework import Homework
from app.models.announcement import Announcement
from app.models.exam import Exam
from app.models.student_enrollment import StudentEnrollment
from app.models.academic_year import AcademicYear
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
        today = date.today()
        active_year = db.query(AcademicYear).filter(
            AcademicYear.school_id == school_id,
            AcademicYear.is_active == True,
        ).first() if school_id else None
        year_id = active_year.id if active_year else None
        stats = crud_dashboard.get_principal_stats(db, school_id=school_id, academic_year_id=year_id)
        exam_query = db.query(Exam).filter(
            Exam.school_id == school_id,
            Exam.start_date >= today,
            func.upper(Exam.status).in_(["SCHEDULED", "MARKS_IN_PROGRESS", "PUBLISHED"]),
        )
        if year_id:
            exam_query = exam_query.filter(Exam.academic_year_id == year_id)
        upcoming_exams = exam_query.order_by(Exam.start_date.asc()).limit(10).all()
        homework_query = db.query(Homework).filter(Homework.school_id == school_id, Homework.is_published == True)
        if year_id:
            homework_query = homework_query.filter(or_(Homework.academic_year_id == year_id, Homework.academic_year_id.is_(None)))
        recent_homework = homework_query.order_by(Homework.created_at.desc()).limit(10).all()
        announcements = db.query(Announcement).filter(
            Announcement.school_id == school_id, Announcement.is_active == True
        ).order_by(Announcement.created_at.desc()).limit(10).all()
        attendance_rows = db.query(Attendance).join(Section, Attendance.section_id == Section.id).filter(
            Section.school_id == school_id, Attendance.date == today
        ).all()
        return PrincipalDashboardResponse(
            total_teachers=stats.get("total_teachers", 0),
            total_students=stats.get("total_students", 0),
            todays_attendance={
                "present": sum(1 for row in attendance_rows if str(row.status).upper() == "PRESENT"),
                "absent": sum(1 for row in attendance_rows if str(row.status).upper() == "ABSENT"),
                "total": len(attendance_rows),
            },
            upcoming_exams=[{"id": e.id, "name": e.name, "start_date": str(e.start_date), "end_date": str(e.end_date), "status": str(e.status)} for e in upcoming_exams],
            recent_homework=[{"id": h.id, "title": h.title, "due_date": str(h.due_date), "grade_id": h.grade_id, "section_id": h.section_id, "subject_id": h.subject_id} for h in recent_homework],
            announcements=[{"id": a.id, "title": a.title, "content": a.content, "created_at": str(a.created_at)} for a in announcements],
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
        today = date.today()
        today_day = today.strftime("%A")
        active_year = db.query(AcademicYear).filter(
            AcademicYear.school_id == school_id,
            AcademicYear.is_active == True,
        ).first()

        # Today's timetable for this teacher
        todays_slots = db.query(Timetable).filter(
            Timetable.teacher_id == teacher.id,
            func.lower(Timetable.day_of_week) == today_day.lower()
        )
        if school_id:
            todays_slots = todays_slots.filter(Timetable.school_id == school_id)
        if active_year:
            todays_slots = todays_slots.filter(Timetable.academic_year_id == active_year.id)
        todays_slots = todays_slots.order_by(Timetable.start_time.asc()).all()

        serialized_timetable = [serialize_timetable(slot) for slot in todays_slots]

        # Check attendance pending for class teacher section
        class_section = db.query(Section).filter(Section.class_teacher_id == teacher.id)
        if school_id:
            class_section = class_section.filter(Section.school_id == school_id)
        class_section = class_section.first()

        attendance_pending = False
        if class_section:
            recorded_count = db.query(Attendance).filter(
                Attendance.section_id == class_section.id,
                Attendance.date == today
            ).count()
            attendance_pending = (recorded_count == 0)

        # Homework summary for this teacher
        hw_query = db.query(Homework).filter(Homework.teacher_id == teacher.id)
        if school_id:
            hw_query = hw_query.filter(Homework.school_id == school_id)
        if active_year:
            hw_query = hw_query.filter(or_(Homework.academic_year_id == active_year.id, Homework.academic_year_id.is_(None)))
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

        upcoming_exams = []
        assignment_rows = db.query(Timetable).filter(
            Timetable.teacher_id == teacher.id,
            Timetable.school_id == school_id,
        ).all()
        assignment_keys = {(row.grade_id, row.section_id, row.subject_id, row.academic_year_id) for row in assignment_rows}
        if assignment_keys:
            for exam in db.query(Exam).filter(
                Exam.school_id == school_id,
                Exam.start_date >= today,
            ).order_by(Exam.start_date.asc()).limit(20).all():
                if any(
                    exam_subject.teacher_id == teacher.id or
                    (exam.grade_id, exam.section_id, exam_subject.subject_id, exam.academic_year_id) in assignment_keys
                    for exam_subject in exam.exam_subjects
                ):
                    upcoming_exams.append({"id": exam.id, "name": exam.name, "start_date": str(exam.start_date), "end_date": str(exam.end_date), "status": str(exam.status)})

        return TeacherDashboardResponse(
            todays_timetable=serialized_timetable,
            attendance_pending=attendance_pending,
            homework_summary=serialized_homework,
            upcoming_exams=upcoming_exams,
            announcements=serialized_announcements,
            calendar_events=[]
        )

    @staticmethod
    def get_student_dashboard(db: Session, current_user: User) -> StudentDashboardResponse:
        student = getattr(current_user, "student_profile", None)
        if not student:
            student = db.query(Student).filter(Student.user_id == current_user.id).first()
        attendance_percentage = 0.0
        pending_homework = []
        upcoming_exams = []
        announcements = []
        todays_timetable = []
        if student:
            records = db.query(Attendance).filter(Attendance.student_id == student.id).all()
            if records:
                present = sum(1 for record in records if str(record.status).upper().endswith("PRESENT"))
                attendance_percentage = round((present / len(records)) * 100, 1)
            enrollment = db.query(StudentEnrollment).filter(
                StudentEnrollment.student_id == student.id,
            ).order_by(StudentEnrollment.id.desc()).first()
            if enrollment and enrollment.section:
                section = enrollment.section
                school_id = student.school_id
                year_id = enrollment.academic_year_id
                pending_homework = db.query(Homework).filter(
                    Homework.school_id == school_id,
                    Homework.grade_id == section.grade_id,
                    Homework.section_id == section.id,
                    Homework.is_published == True,
                    Homework.due_date >= date.today(),
                    or_(Homework.academic_year_id == year_id, Homework.academic_year_id.is_(None)),
                ).order_by(Homework.due_date.asc()).all()
                upcoming_exams = db.query(Exam).filter(
                    Exam.school_id == school_id,
                    Exam.academic_year_id == year_id,
                    Exam.grade_id == section.grade_id,
                    Exam.section_id == section.id,
                    Exam.start_date >= date.today(),
                    func.upper(Exam.status).in_(["SCHEDULED", "MARKS_IN_PROGRESS", "PUBLISHED"]),
                ).order_by(Exam.start_date.asc()).all()
                todays_timetable = db.query(Timetable).filter(
                    Timetable.school_id == school_id,
                    Timetable.academic_year_id == year_id,
                    Timetable.grade_id == section.grade_id,
                    Timetable.section_id == section.id,
                    func.lower(Timetable.day_of_week) == date.today().strftime("%A").lower(),
                ).order_by(Timetable.start_time.asc()).all()
                announcements = db.query(Announcement).filter(
                    Announcement.school_id == school_id,
                    Announcement.is_active == True,
                    or_(
                        Announcement.target_role.is_(None),
                        func.upper(Announcement.target_role).in_(["ALL", "SCHOOL_WIDE", "STUDENT"]),
                        and_(Announcement.grade_id == section.grade_id, Announcement.section_id.is_(None)),
                        and_(Announcement.grade_id == section.grade_id, Announcement.section_id == section.id),
                    ),
                ).order_by(Announcement.created_at.desc()).limit(10).all()
        return StudentDashboardResponse(
            todays_timetable=[serialize_timetable(slot) for slot in todays_timetable],
            attendance_percentage=attendance_percentage,
            pending_homework=[{"id": h.id, "title": h.title, "due_date": str(h.due_date), "grade_id": h.grade_id, "section_id": h.section_id, "subject_id": h.subject_id} for h in pending_homework],
            upcoming_exams=[{"id": e.id, "name": e.name, "start_date": str(e.start_date), "end_date": str(e.end_date), "status": str(e.status)} for e in upcoming_exams],
            latest_marks=[],
            report_card_summary=None,
            announcements=[{"id": a.id, "title": a.title, "content": a.content, "created_at": str(a.created_at)} for a in announcements],
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
