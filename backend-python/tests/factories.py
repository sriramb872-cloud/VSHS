"""Object factories for the pytest suite (no external dependency).

Every factory returns a *persisted* row (``flush``), so IDs are available
immediately. All rows created during a test are wiped by the ``db`` fixture
before the next test, so tests do not need to clean up after themselves.

Attribute names follow the real model definitions exactly (e.g. ``mobile`` not
``mobile_number`` — the latter is only the *column* name).
"""

from __future__ import annotations

import itertools
from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.academic_year import AcademicYear
from app.models.announcement import Announcement
from app.models.attendance import Attendance
from app.models.calendar_event import CalendarEvent
from app.models.exam import Exam
from app.models.exam_subject import ExamSubject
from app.models.grade import Grade
from app.models.grade_subject import GradeSubject
from app.models.homework import Homework
from app.models.marks import Marks
from app.models.notification import Notification
from app.models.report_card import ReportCard
from app.models.school import School
from app.models.section import Section
from app.models.student import Student
from app.models.student_enrollment import StudentEnrollment
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.timetable import Timetable
from app.models.upload import Upload
from app.models.user import User

# Monotonic across the whole session: identifiers stay unique even though the
# database is wiped between tests.
_seq = itertools.count(1)

# bcrypt hashing dominates suite runtime (~100ms/row); the same password
# always yields the same verification behaviour, so hash each distinct
# password once and reuse the digest.
_HASH_CACHE: dict[str, str] = {}

DEFAULT_PASSWORD = "Password123!"


def hash_password_once(password: str) -> str:
    if password not in _HASH_CACHE:
        _HASH_CACHE[password] = get_password_hash(password)
    return _HASH_CACHE[password]


def make_school(db: Session, **overrides) -> School:
    n = next(_seq)
    school = School(
        name=overrides.pop("name", f"Test School {n}"),
        code=overrides.pop("code", f"TST{n:04d}"),
        contact_email=overrides.pop("contact_email", f"school{n}@example.com"),
        is_active=overrides.pop("is_active", True),
        **overrides,
    )
    db.add(school)
    db.flush()
    return school


def make_user(
    db: Session,
    school: Optional[School] = None,
    role: str = "TEACHER",
    password: str = DEFAULT_PASSWORD,
    **overrides,
) -> User:
    n = next(_seq)
    user = User(
        school_id=overrides.pop("school_id", school.id if school else None),
        mobile=overrides.pop("mobile", f"9{n:010d}"),
        email=overrides.pop("email", f"user{n}@example.com"),
        password_hash=hash_password_once(password),
        display_name=overrides.pop("display_name", f"{role.title()} {n}"),
        role=role,
        is_active=overrides.pop("is_active", "ACTIVE"),
        must_change_password=overrides.pop("must_change_password", False),
        **overrides,
    )
    db.add(user)
    db.flush()
    return user


def make_teacher(
    db: Session,
    school: School,
    user: Optional[User] = None,
    **overrides,
) -> Teacher:
    user = user or make_user(db, school, role="TEACHER")
    teacher = Teacher(
        user_id=user.id,
        school_id=school.id,
        employee_id=overrides.pop("employee_id", f"EMP{next(_seq):06d}"),
        **overrides,
    )
    db.add(teacher)
    db.flush()
    return teacher


def make_student(
    db: Session,
    school: School,
    user: Optional[User] = None,
    **overrides,
) -> Student:
    user = user or make_user(db, school, role="STUDENT")
    student = Student(
        user_id=user.id,
        school_id=school.id,
        admission_number=overrides.pop("admission_number", f"ADM{next(_seq):06d}"),
        **overrides,
    )
    db.add(student)
    db.flush()
    return student


def make_grade(db: Session, school: School, name: Optional[str] = None, **overrides) -> Grade:
    n = next(_seq)
    grade = Grade(
        school_id=school.id,
        name=name or f"Grade {n}",
        code=overrides.pop("code", f"G{n:03d}"),
        display_order=overrides.pop("display_order", n),
        **overrides,
    )
    db.add(grade)
    db.flush()
    return grade


def make_section(
    db: Session,
    grade: Grade,
    name: Optional[str] = None,
    class_teacher_id: Optional[int] = None,
    **overrides,
) -> Section:
    section = Section(
        grade_id=grade.id,
        school_id=grade.school_id,
        name=name or f"{grade.name}-A",
        class_teacher_id=class_teacher_id,
        **overrides,
    )
    db.add(section)
    db.flush()
    return section


def make_subject(db: Session, school: School, name: Optional[str] = None, **overrides) -> Subject:
    n = next(_seq)
    subject = Subject(
        school_id=school.id,
        name=name or f"Subject {n}",
        code=overrides.pop("code", f"S{n:03d}"),
        **overrides,
    )
    db.add(subject)
    db.flush()
    return subject


def make_academic_year(
    db: Session,
    school: School,
    *,
    name: Optional[str] = None,
    start: date = date(2025, 4, 1),
    end: date = date(2026, 3, 31),
    is_current: bool = True,
    status: str = "ACTIVE",
    **overrides,
) -> AcademicYear:
    year = AcademicYear(
        school_id=school.id,
        name=name or f"{start.year}-{end.year}",
        start_date=start,
        end_date=end,
        is_active=is_current,
        status=status,
        **overrides,
    )
    db.add(year)
    db.flush()
    return year


def make_enrollment(
    db: Session,
    student: Student,
    academic_year: AcademicYear,
    section: Section,
    roll_number: Optional[str] = None,
) -> StudentEnrollment:
    enrollment = StudentEnrollment(
        student_id=student.id,
        academic_year_id=academic_year.id,
        section_id=section.id,
        roll_number=roll_number or f"R{next(_seq):04d}",
    )
    db.add(enrollment)
    db.flush()
    return enrollment


def make_exam(
    db: Session,
    school: School,
    academic_year: AcademicYear,
    grade: Grade,
    section: Section,
    **overrides,
) -> Exam:
    exam = Exam(
        school_id=school.id,
        academic_year_id=academic_year.id,
        grade_id=grade.id,
        section_id=section.id,
        name=overrides.pop("name", "Mid Term"),
        exam_type=overrides.pop("exam_type", "Summative Assessment"),
        assessment_mode=overrides.pop("assessment_mode", "SUMMATIVE"),
        start_date=overrides.pop("start_date", date(2025, 9, 1)),
        end_date=overrides.pop("end_date", date(2025, 9, 10)),
        status=overrides.pop("status", "SCHEDULED"),
        **overrides,
    )
    db.add(exam)
    db.flush()
    return exam


def make_exam_subject(
    db: Session,
    exam: Exam,
    subject: Subject,
    **overrides,
) -> ExamSubject:
    exam_subject = ExamSubject(
        exam_id=exam.id,
        subject_id=subject.id,
        exam_date=overrides.pop("exam_date", exam.start_date),
        maximum_marks=overrides.pop("maximum_marks", 100.0),
        passing_marks=overrides.pop("passing_marks", 35.0),
        **overrides,
    )
    db.add(exam_subject)
    db.flush()
    return exam_subject


def make_homework(
    db: Session,
    school: School,
    teacher: Teacher,
    grade: Grade,
    section: Section,
    subject: Subject,
    academic_year: AcademicYear,
    **overrides,
) -> Homework:
    homework = Homework(
        school_id=school.id,
        academic_year_id=academic_year.id,
        teacher_id=teacher.id,
        grade_id=grade.id,
        section_id=section.id,
        subject_id=subject.id,
        title=overrides.pop("title", "Chapter 1"),
        description=overrides.pop("description", "Do exercises 1-5"),
        assigned_date=overrides.pop("assigned_date", date(2025, 6, 1)),
        due_date=overrides.pop("due_date", date(2025, 6, 10)),
        is_published=overrides.pop("is_published", True),
        **overrides,
    )
    db.add(homework)
    db.flush()
    return homework


def make_attendance(
    db: Session,
    student: Student,
    section: Section,
    academic_year: AcademicYear,
    day: date = date(2025, 6, 3),
    status: str = "PRESENT",
    **overrides,
) -> Attendance:
    record = Attendance(
        student_id=student.id,
        section_id=section.id,
        date=day,
        status=status,
        academic_year_id=academic_year.id,
        **overrides,
    )
    db.add(record)
    db.flush()
    return record


def make_announcement(
    db: Session,
    school: School,
    created_by: Optional[User] = None,
    **overrides,
) -> Announcement:
    announcement = Announcement(
        school_id=school.id,
        created_by=created_by.id if created_by else None,
        title=overrides.pop("title", "Holiday notice"),
        content=overrides.pop("content", "School remains closed tomorrow."),
        publish_date=overrides.pop("publish_date", datetime.utcnow()),
        is_active=overrides.pop("is_active", True),
        **overrides,
    )
    db.add(announcement)
    db.flush()
    return announcement


def make_calendar_event(db: Session, school: School, **overrides) -> CalendarEvent:
    event = CalendarEvent(
        school_id=school.id,
        title=overrides.pop("title", "Sports Day"),
        event_type=overrides.pop("event_type", "EVENT"),
        start_date=overrides.pop("start_date", date(2025, 8, 15)),
        end_date=overrides.pop("end_date", date(2025, 8, 15)),
        is_active=overrides.pop("is_active", True),
        **overrides,
    )
    db.add(event)
    db.flush()
    return event


def make_report_card(
    db: Session,
    student: Student,
    academic_year: AcademicYear,
    exam: Optional[Exam] = None,
    **overrides,
) -> ReportCard:
    card = ReportCard(
        student_id=student.id,
        academic_year_id=academic_year.id,
        exam_id=exam.id if exam else None,
        term_name=overrides.pop("term_name", "Term 1"),
        total_marks=overrides.pop("total_marks", 420.0),
        percentage=overrides.pop("percentage", 84.0),
        **overrides,
    )
    db.add(card)
    db.flush()
    return card


def make_marks(
    db: Session,
    exam_subject: ExamSubject,
    student: Student,
    school: School,
    marks_obtained: float = 80.0,
    **overrides,
) -> Marks:
    row = Marks(
        exam_subject_id=exam_subject.id,
        student_id=student.id,
        school_id=school.id,
        marks_obtained=marks_obtained,
        max_marks=overrides.pop("max_marks", exam_subject.maximum_marks),
        **overrides,
    )
    db.add(row)
    db.flush()
    return row


def make_timetable(
    db: Session,
    school: School,
    academic_year: AcademicYear,
    grade: Grade,
    section: Section,
    subject: Subject,
    teacher: Teacher,
    **overrides,
) -> Timetable:
    row = Timetable(
        # SQLite only autoincrements INTEGER primary keys, and this model maps
        # ``id`` to a BIGINT column (autoincrement works on MySQL in prod).
        # Set the id explicitly so the factory works on both backends.
        id=next(_seq),
        school_id=school.id,
        academic_year_id=academic_year.id,
        grade_id=grade.id,
        section_id=section.id,
        subject_id=subject.id,
        teacher_id=teacher.id,
        day_of_week=overrides.pop("day_of_week", "MONDAY"),
        start_time=overrides.pop("start_time", time(9, 0)),
        end_time=overrides.pop("end_time", time(9, 45)),
        **overrides,
    )
    db.add(row)
    db.flush()
    return row


def make_teacher_subject(
    db: Session,
    teacher: Teacher,
    subject: Subject,
    grade: Grade,
    section: Section,
    school: School,
    **overrides,
) -> TeacherSubject:
    row = TeacherSubject(
        teacher_id=teacher.id,
        subject_id=subject.id,
        grade_id=grade.id,
        section_id=section.id,
        school_id=school.id,
        academic_year_id=overrides.pop("academic_year_id", None),
    )
    db.add(row)
    db.flush()
    return row


def make_grade_subject(
    db: Session,
    grade: Grade,
    subject: Subject,
    teacher: Optional[Teacher] = None,
) -> GradeSubject:
    row = GradeSubject(
        # BIGINT PK: SQLite won't autoincrement it (MySQL does in prod).
        id=next(_seq),
        grade_id=grade.id,
        subject_id=subject.id,
        teacher_id=teacher.id if teacher else None,
    )
    db.add(row)
    db.flush()
    return row


def make_notification(
    db: Session,
    school: School,
    sender: Optional[User] = None,
    **overrides,
) -> Notification:
    row = Notification(
        school_id=school.id,
        sender_id=sender.id if sender else None,
        sender_role=overrides.pop("sender_role", "PRINCIPAL"),
        notification_type=overrides.pop("notification_type", "PUBLIC"),
        title=overrides.pop("title", "Notice"),
        message=overrides.pop("message", "Please read."),
        category=overrides.pop("category", "PUBLIC"),
        **overrides,
    )
    db.add(row)
    db.flush()
    return row


def make_upload(
    db: Session,
    school: School,
    uploaded_by: Optional[User] = None,
    **overrides,
) -> Upload:
    n = next(_seq)
    row = Upload(
        filename=overrides.pop("filename", f"file{n}.png"),
        original_filename=overrides.pop("original_filename", f"photo{n}.png"),
        file_path=overrides.pop("file_path", f"/uploads/{n}.png"),
        content_type=overrides.pop("content_type", "image/png"),
        file_size=overrides.pop("file_size", 1024),
        school_id=school.id,
        uploaded_by_id=uploaded_by.id if uploaded_by else None,
        **overrides,
    )
    db.add(row)
    db.flush()
    return row
