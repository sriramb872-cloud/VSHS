# Testing

## Running the suite

```bash
cd backend-python
pip install -r requirements.txt -r requirements-dev.txt

pytest -q                          # default: SQLite-only, skips MySQL tests
```

Optional (also what CI does): run the migration tests against a **disposable**
MySQL database:

```bash
export MIGRATION_TEST_DATABASE_URL=mysql+pymysql://root:PASS@127.0.0.1:3306/scholaris_ci
pytest -q
```

Lint gate:

```bash
ruff check .
```

## How the test database works

`tests/conftest.py` sets every environment variable **before** any application
import (config reads env at import time), then:

* creates an isolated, file-backed SQLite database (never the configured MySQL
  server) with a single shared connection (`StaticPool`) and `PRAGMA foreign_keys=ON`;
* **wipes every table before each test** (routers use their own sessions and
  commit, so rollback-per-test is not an option);
* overrides `app.api.deps.get_db` so HTTP requests go through the same session;
* points `/ready`'s engine at the test engine so no probe ever touches a real DB.

Data is built with **factories** (`tests/factories.py`) and the composite
fixture `world` (`tests/world.py`), which builds **two complete, independent
schools (A and B)** — principal, teacher, student, grade, section, subject,
year, exam (+subject), homework, announcement, event, attendance, report card,
marks — plus a platform super-admin. `tests/helpers.py::auth()` mints real
access tokens through the production `issue_session` path (bcrypt login itself
is covered end-to-end in `test_auth.py`).

## Layout

| File | Covers |
|---|---|
| `tests/test_health_cors.py` | `/health`, `/ready` (503 on DB failure), CORS allow/deny, security headers |
| `tests/test_auth.py` | login, refresh rotation, revocation, token version, lockout, password flows, enumeration |
| `tests/test_tenant_isolation.py` | security matrix A–H, core domains |
| `tests/test_tenant_isolation_extended.py` | security matrix A–H, remaining domains + fix regressions |
| `tests/test_migrations.py` | Alembic vs MySQL (gated, see `MIGRATIONS.md`) |

## Security tests A–H (mandatory, both tenant suites)

Every tenant-scoped domain (grades, sections, subjects, students, users,
academic years, exams, homework, announcements, calendar events, attendance,
report cards, marks, dashboard, teachers, principals, timetables,
teacher-subjects, teacher-assignments, grade-subjects, student-enrollments,
notifications, search, files) is covered by:

| ID | Requirement |
|---|---|
| **A** | Cross-tenant **read** of an object is denied (403 “exists but not yours” or 404 “no existence oracle”, per-domain convention) |
| **B** | Cross-tenant **write** (PATCH/PUT/POST) is denied and nothing is mutated |
| **C** | Cross-tenant **delete** is denied and the row survives |
| **D** | **Create** with foreign-school references is rejected and no row persists |
| **E** | **List** endpoints only ever return the caller's school; foreign filter params narrow to empty, never widen |
| **F** | A non-super-admin without tenant context **fails closed** (403 `School context missing for this account`) on every route — enforced centrally in `app/api/deps.py::get_current_active_user` |
| **G** | `SUPER_ADMIN` keeps deliberate cross-school access (reads, writes, unfiltered lists) |
| **H** | Role gates hold (student/teacher/principal vs staff and super-admin surfaces) |

### Fix-regression tests (in `test_tenant_isolation_extended.py`)

* notification class-teacher lookup is school-scoped (no roster leak via a
  stray cross-tenant `class_teacher_id`);
* search teacher-subject results are school-scoped on **both** layers
  (assignment row filter + subject school filter);
* `GET /teacher-assignments` filters timetables by school for non-super-admins;
* deleting an orphaned enrollment (student row missing) fails closed for
  non-super-admins.

## CI

`.github/workflows/ci.yml` on every push/PR:

1. **backend**: Python 3.12 → install → `ruff check .` → `pytest -q`
   (SQLite functional/security suite **plus** the MySQL 8.4 migration suite
   against a service container). A failing test fails the build.
2. **frontend**: `npm ci` → `npm run lint` (eslint) → `npm run typecheck`
   (`tsc --noEmit`) → `npm run build` (vite).

There is no backend type-checker configured; lint + tests are the gate.
