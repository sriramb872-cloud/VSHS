"""Ad-hoc inspection helper (QA only). Not part of the application."""
import sys

sys.path.insert(0, ".")

from sqlalchemy import inspect, text  # noqa: E402

from app.core.database import engine  # noqa: E402

insp = inspect(engine)
tables = sorted(insp.get_table_names())

print("== table count ==", len(tables))
for t in ("uploads", "roles", "attendance_records", "students", "sections", "schools", "users"):
    print(f"table {t!r} exists:", t in tables)

print("\n== attendance_records.status column ==")
for row in insp.get_columns("attendance_records"):
    if row["name"] == "status":
        print("  type:", row["type"])
        print("  enum values:", getattr(row["type"], "enums", None))

print("\n== is Upload registered in app.models? ==")
import app.models as m  # noqa: E402

print("  Upload in app.models:", hasattr(m, "Upload"))
print("  Role in app.models:", hasattr(m, "Role"))
from app.models.role import UserRole  # noqa: E402

print("  UserRole members:", [r.value for r in UserRole])

print("\n== roles table columns ==")
for row in insp.get_columns("roles"):
    print("  ", row["name"], row["type"], "nullable=", row["nullable"])

print("\n== columns of uploads (if present) ==")
if "uploads" in tables:
    for row in insp.get_columns("uploads"):
        print("  ", row["name"], row["type"], "nullable=", row["nullable"])

print("\n== profile_photos dir ==")
import os  # noqa: E402

d = os.path.abspath(os.path.join("media", "profile_photos"))
print("  exists:", os.path.isdir(d))
if os.path.isdir(d):
    files = os.listdir(d)
    total = sum(os.path.getsize(os.path.join(d, f)) for f in files)
    print("  files:", len(files), "bytes:", total)

print("\n== media dir ==")
m = os.path.abspath("media")
if os.path.isdir(m):
    tot = 0
    n = 0
    for root, _dirs, fnames in os.walk(m):
        for f in fnames:
            tot += os.path.getsize(os.path.join(root, f))
            n += 1
    print("  files:", n, "bytes:", tot)

print("\n== sanity: db round trip ==")
with engine.connect() as c:
    print("  SELECT 1 ->", c.execute(text("SELECT 1")).scalar())
