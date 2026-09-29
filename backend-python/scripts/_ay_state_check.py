import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine

QUERIES = [
    ("AY", "SELECT academic_year_id, school_id, year_name, is_current, status, start_date, end_date FROM academic_years"),
    ("ATT", "SELECT attendance_id, student_id, date, academic_year_id FROM attendance_records"),
    ("TS", "SELECT id, school_id, grade_id, section_id, subject_id, academic_year_id FROM teacher_subjects"),
    ("SET", "SELECT school_id, academic_year FROM school_settings"),
    ("IDX-ts", "SELECT index_name, non_unique, GROUP_CONCAT(column_name ORDER BY seq_in_index) FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='teacher_subjects' GROUP BY index_name, non_unique"),
    ("IDX-att", "SELECT index_name, non_unique, GROUP_CONCAT(column_name ORDER BY seq_in_index) FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='attendance_records' GROUP BY index_name, non_unique"),
    ("IDX-se", "SELECT index_name, non_unique, GROUP_CONCAT(column_name ORDER BY seq_in_index) FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='student_enrollments' GROUP BY index_name, non_unique"),
    ("IDX-ay", "SELECT index_name, non_unique, GROUP_CONCAT(column_name ORDER BY seq_in_index) FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='academic_years' GROUP BY index_name, non_unique"),
]

with engine.connect() as c:
    for label, sql in QUERIES:
        print("---", label)
        try:
            for r in c.execute(text(sql)):
                print("  ", tuple(r))
        except Exception as exc:  # noqa: BLE001
            print("   ERROR:", exc)
