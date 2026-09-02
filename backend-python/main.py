# backend-python/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
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
    teacher_assignments,
    audit_logs,
    files,
    search,
    slip_tests,
)

Base.metadata.create_all(bind=engine)

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
app.include_router(teacher_assignments.router, prefix=PREFIX)
app.include_router(audit_logs.router, prefix=PREFIX)
app.include_router(files.router, prefix=PREFIX)
app.include_router(search.router, prefix=PREFIX)
app.include_router(slip_tests.router, prefix=PREFIX)
