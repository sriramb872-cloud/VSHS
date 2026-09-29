import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine

SQL = (
    "SELECT table_name, column_name, column_type, is_nullable "
    "FROM information_schema.columns "
    "WHERE table_schema = DATABASE() "
    "AND table_name IN ('attendance_records', 'teacher_subjects', 'student_enrollments', 'academic_years') "
    "ORDER BY table_name, ordinal_position"
)

with engine.connect() as conn:
    for r in conn.execute(text(SQL)):
        print(f"{r[0]:24} {r[1]:24} {r[2]:30} {r[3]}")
