"""QA check: print the live MySQL ENUM value list for a column.

Read-only helper used to confirm startup enum reconciliation actually widened
the column (e.g. attendance_records.status gaining 'VOID').

Usage:
    python scripts/qa_show_enum.py attendance_records status
    python scripts/qa_show_enum.py users role
"""
import sys

sys.path.insert(0, ".")

from sqlalchemy import inspect

from app.core.database import engine


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)

    table_name, column_name = sys.argv[1], sys.argv[2]
    inspector = inspect(engine)
    for column in inspector.get_columns(table_name):
        if column["name"] != column_name:
            continue
        values = list(getattr(column.get("type"), "enums", None) or [])
        print(f"{table_name}.{column_name} type={column['type']} enums={values}")
        return

    print(f"{table_name}.{column_name} not found")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
