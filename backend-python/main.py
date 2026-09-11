# backend-python/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from sqlalchemy import inspect, text
import app.models  # Ensure all models are registered in Base.metadata

from app.routers.v1 import (
    auth,
    dashboard,
    homework,
    exam,
    marks,
    report_card,
    timetable,
    announcement,
    notification,
    calendar_event,
    settings,
    academic_years,
    schools,
    grades,
    sections,
    subjects,
    teachers,
    students,
    principals,
    users,
    attendance,
    student_enrollments,
    grade_subjects,
    teacher_subjects,
    teacher_assignments,
    audit_logs,
    files,
    search,
    slip_tests,
)

Base.metadata.create_all(bind=engine)

# Lightweight schema migration for installations without Alembic.
# ExamSubject dates are nullable so existing exam schedules remain readable.
with engine.begin() as _conn:
    _columns = {column["name"] for column in inspect(engine).get_columns("exam_subjects")}
    if _columns and "exam_date" not in _columns:
        _conn.execute(text("ALTER TABLE exam_subjects ADD COLUMN exam_date DATE NULL"))
    _homework_columns = {column["name"] for column in inspect(engine).get_columns("homework")}
    if _homework_columns and "academic_year_id" not in _homework_columns:
        _conn.execute(text("ALTER TABLE homework ADD COLUMN academic_year_id INT NULL"))
    if _homework_columns:
        _conn.execute(text("UPDATE homework h JOIN academic_years ay ON ay.school_id = h.school_id AND ay.is_current = 1 SET h.academic_year_id = ay.academic_year_id WHERE h.academic_year_id IS NULL"))
    _report_card_columns = {column["name"] for column in inspect(engine).get_columns("report_cards")}
    if _report_card_columns and "exam_id" not in _report_card_columns:
        _conn.execute(text("ALTER TABLE report_cards ADD COLUMN exam_id INT NULL"))
    if _report_card_columns:
        # Older installations used (student, year, term) as the unique key,
        # which prevents generating a card for a specific exam when a legacy
        # card already exists.  Replace it with the exam-aware identity.
        _report_card_unique = inspect(engine).get_unique_constraints("report_cards")
        _legacy_unique = next((item for item in _report_card_unique if item.get("name") == "uq_student_term_report_card"), None)
        if _legacy_unique:
            _conn.execute(text("ALTER TABLE report_cards DROP INDEX uq_student_term_report_card"))
        _current_unique = inspect(engine).get_unique_constraints("report_cards")
        if not any(item.get("name") == "uq_student_exam_term_report_card" for item in _current_unique):
            _conn.execute(text("ALTER TABLE report_cards ADD CONSTRAINT uq_student_exam_term_report_card UNIQUE (student_id, academic_year_id, exam_id, term_name)"))

app = FastAPI(
    title="SCHOLARIS School ERP API",
    description="Production-ready multi-school ERP backend for SCHOLARIS V1",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Configuration for Frontend Development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static and Media Files
import os
from fastapi.staticfiles import StaticFiles

media_path = os.path.join(os.path.dirname(__file__), "media")
os.makedirs(media_path, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_path), name="media")

# Root Endpoints
@app.get("/", tags=["Root"])
async def root():
    return {
        "app": "SCHOLARIS School ERP API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}

# Register API Routers under /api/v1 prefix
PREFIX = "/api/v1"

app.include_router(auth.router, prefix=PREFIX)
app.include_router(dashboard.router, prefix=PREFIX)
app.include_router(homework.router, prefix=PREFIX)
app.include_router(exam.router, prefix=PREFIX)
app.include_router(marks.router, prefix=PREFIX)
app.include_router(report_card.router, prefix=PREFIX)
app.include_router(timetable.router, prefix=PREFIX)
app.include_router(announcement.router, prefix=PREFIX)
app.include_router(notification.router, prefix=PREFIX)
app.include_router(calendar_event.router, prefix=PREFIX)
app.include_router(settings.router, prefix=PREFIX)
app.include_router(academic_years.router, prefix=PREFIX)
app.include_router(schools.router, prefix=PREFIX)
app.include_router(grades.router, prefix=PREFIX)
app.include_router(sections.router, prefix=PREFIX)
app.include_router(subjects.router, prefix=PREFIX)
app.include_router(teachers.router, prefix=PREFIX)
app.include_router(students.router, prefix=PREFIX)
app.include_router(principals.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(attendance.router, prefix=PREFIX)
app.include_router(student_enrollments.router, prefix=PREFIX)
app.include_router(grade_subjects.router, prefix=PREFIX)
app.include_router(teacher_subjects.router, prefix=PREFIX)
app.include_router(teacher_assignments.router, prefix=PREFIX)
app.include_router(audit_logs.router, prefix=PREFIX)
app.include_router(files.router, prefix=PREFIX)
app.include_router(search.router, prefix=PREFIX)
app.include_router(slip_tests.router, prefix=PREFIX)
