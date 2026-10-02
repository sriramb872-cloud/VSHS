"""Composite fixtures: two complete, independent schools (A and B).

Each school gets its own principal, teacher (+ profile), student (+ profile),
grade, section, subject, academic year, enrollment, exam + exam subject,
homework, announcement, calendar event, attendance record, report card and
marks row — i.e. one object of every tenant-scoped domain, so tests can prove
school A can never touch school B.
"""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.orm import Session

from tests.factories import (
    make_academic_year,
    make_announcement,
    make_attendance,
    make_calendar_event,
    make_enrollment,
    make_exam,
    make_exam_subject,
    make_grade,
    make_homework,
    make_marks,
    make_report_card,
    make_school,
    make_section,
    make_student,
    make_subject,
    make_teacher,
    make_user,
)


def build_school(db: Session, tag: str) -> SimpleNamespace:
    school = make_school(db, name=f"School {tag}", code=f"SCH{tag}")

    principal = make_user(db, school, role="PRINCIPAL", display_name=f"Principal {tag}")

    teacher_user = make_user(db, school, role="TEACHER", display_name=f"Teacher {tag}")
    teacher = make_teacher(db, school, user=teacher_user)

    student_user = make_user(db, school, role="STUDENT", display_name=f"Student {tag}")
    student = make_student(db, school, user=student_user)

    grade = make_grade(db, school, name=f"Grade {tag}")
    section = make_section(db, grade, name=tag, class_teacher_id=teacher.id)
    subject = make_subject(db, school, name=f"Subject {tag}")
    year = make_academic_year(db, school, name=f"2025-{tag}")

    make_enrollment(db, student, year, section)

    exam = make_exam(db, school, year, grade, section, name=f"Exam {tag}")
    exam_subject = make_exam_subject(db, exam, subject, teacher_id=teacher.id)
    homework = make_homework(db, school, teacher, grade, section, subject, year)
    announcement = make_announcement(db, school, created_by=principal)
    event = make_calendar_event(db, school, title=f"Event {tag}")
    attendance = make_attendance(db, student, section, year)
    report_card = make_report_card(db, student, year, exam)
    marks = make_marks(db, exam_subject, student, school, marks_obtained=88.0)

    return SimpleNamespace(
        tag=tag,
        school=school,
        principal=principal,
        teacher_user=teacher_user,
        teacher=teacher,
        student_user=student_user,
        student=student,
        grade=grade,
        section=section,
        subject=subject,
        year=year,
        exam=exam,
        exam_subject=exam_subject,
        homework=homework,
        announcement=announcement,
        event=event,
        attendance=attendance,
        report_card=report_card,
        marks=marks,
    )
