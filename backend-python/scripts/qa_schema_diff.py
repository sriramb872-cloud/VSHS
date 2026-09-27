"""QA diagnostic: compare the live MySQL schema against the SQLAlchemy ORM metadata.

Read-only. Prints every table/column that exists in the ORM but not in the
database so schema drift (the cause of the dashboard 500) can be seen in full.
"""
import sys

sys.path.insert(0, ".")

from sqlalchemy import inspect

import app.models  # noqa: F401  (registers every model on Base.metadata)
from app.core.database import Base, engine

Dialect = {}


def ddl_for(col):
    try:
        return col.type.compile(Dialect)
    except Exception:  # pragma: no cover - defensive
        t = str(col.type)
        return t.upper()


def main():
    insp = inspect(engine)
    db_tables = set(insp.get_table_names())
    missing_tables = []
    missing_cols = []
    for table in Base.metadata.sorted_tables:
        if table.name not in db_tables:
            missing_tables.append(table.name)
            continue
        have = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name not in have:
                nullable = "NULL" if col.nullable else "NOT NULL"
                default = ""
                if col.default is not None and getattr(col.default, "is_scalar", False):
                    default = f" DEFAULT {col.default.arg!r}"
                missing_cols.append(
                    f"{table.name}.{col.name} {ddl_for(col)} {nullable}{default}"
                )

    print("=== TABLES IN ORM BUT NOT IN DB ===")
    print("\n".join(missing_tables) or "(none)")
    print()
    print("=== COLUMNS IN ORM BUT NOT IN DB ===")
    print("\n".join(missing_cols) or "(none)")


if __name__ == "__main__":
    main()
