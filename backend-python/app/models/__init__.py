# backend-python/app/models/__init__.py
from app.models.school import School
from app.models.user import User
from app.models.academic_year import AcademicYear
from app.models.grade import Grade
from app.models.section import Section
from app.models.subject import Subject
from app.models.grade_subject import GradeSubject
from app.models.principal import Principal
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from app.models.attendance import Attendance
from app.models.attendance_record import AttendanceRecord
from app.models.homework import Homework
from app.models.exam import Exam
from app.models.exam_subject import ExamSubject
from app.models.exam_result import ExamResult
from app.models.marks import Marks
from app.models.report_card import ReportCard
from app.models.announcement import Announcement
from app.models.notification import Notification
from app.models.calendar_event import CalendarEvent
from app.models.timetable import Timetable
from app.models.audit_log import AuditLog
from app.models.role import Role

__all__ = [
    "School",
    "User",
    "AcademicYear",
    "Grade",
    "Section",
    "Subject",
    "GradeSubject",
    "Principal",
    "Teacher",
    "TeacherSubject",
    "Student",
    "StudentEnrollment",
    "Attendance",
    "AttendanceRecord",
    "Homework",
    "Exam",
    "ExamSubject",
    "ExamResult",
    "Marks",
    "ReportCard",
    "Announcement",
    "Notification",
    "CalendarEvent",
    "Timetable",
    "AuditLog",
    "Role",
]