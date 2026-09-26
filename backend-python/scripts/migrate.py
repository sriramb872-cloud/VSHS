import sys
from pathlib import Path

from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, engine
import app.models  # Ensure all models are registered in Base.metadata


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
    _user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if _user_columns and "must_change_password" not in _user_columns:
        _conn.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT FALSE"))
    _att_columns = {column["name"] for column in inspect(engine).get_columns("attendance_records")}
    if _att_columns and "remarks" not in _att_columns:
        _conn.execute(text("ALTER TABLE attendance_records ADD COLUMN remarks VARCHAR(255) NULL"))
    try:
        _conn.execute(text("ALTER TABLE attendance_records MODIFY COLUMN status ENUM('PRESENT', 'ABSENT', 'LATE', 'LEAVE', 'VOID') NOT NULL"))
    except Exception:
        pass
    try:
        _conn.execute(text("ALTER TABLE exams MODIFY COLUMN status ENUM('SCHEDULED', 'MARKS_IN_PROGRESS', 'PUBLISHED', 'ARCHIVED') NOT NULL DEFAULT 'SCHEDULED'"))
    except Exception:
        pass
