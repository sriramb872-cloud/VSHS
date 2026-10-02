# Database Migrations (Alembic)

## Policy

* **Alembic is the only schema mechanism.** No import-time DDL, no
  `Base.metadata.create_all()` in any startup path, no hand-run `ALTER`
  scripts. (`scripts/migrate.py` was removed for exactly this reason; its
  one-off repairs live on, guarded, in `app/core/schema_repair.py`.)
* **Migrations run exactly once per deploy, before workers start** — see
  `start.sh`: `alembic upgrade head && gunicorn ...`.
* **Existing revisions are frozen.** Once a revision has ever run anywhere,
  never edit it. Schema changes are always a *new* revision.
* **Never drop or reset production data.** Downgrades exist for development
  and for verified rollbacks only.

## Revision conventions

| Revision | Role |
|---|---|
| `0001_initial_schema` | Frozen full schema (the canonical starting point for fresh installs) |
| `0002_legacy_schema_repair` | Calls `repair_database()` to bring pre-Alembic installs up to the model schema without losing data |
| `0003+` | Every subsequent change, one revision per change, frozen after release |

## Commands

Run from `backend-python/` with `DATABASE_URL` set (local `.env` is read
automatically and never overrides real environment variables):

```bash
alembic current                 # where is this database?
alembic heads                   # expected head (single head, always)
alembic upgrade head            # apply everything (this is what start.sh runs)
alembic downgrade <revision>    # roll back to a specific revision
alembic check                   # fail if models and migrations drift apart
alembic revision --autogenerate -m "describe the change"
```

After autogenerating, **review the generated script** and freeze it: the
migration chain must always produce exactly `Base.metadata.tables`.

## Workflows

### Fresh installation (empty database)

```bash
alembic upgrade head
```

Creates every table (32 at head `0002`) plus `alembic_version`.

### Existing legacy installation (created via `schemadeploy.sql` / old SQL dumps)

```bash
alembic upgrade head
```

`0002` detects the legacy layout and adds what is missing (auth columns
`token_version`, `locked_until`, `must_change_password`, the `refresh_tokens`
table, foreign keys, indexes, ...) while **preserving every existing row**.

### Deploying a new revision

1. Author the revision (autogenerate + review).
2. `alembic upgrade head` against a scratch database.
3. Run the migration test suite (below).
4. Ship. `start.sh` applies it before the new workers accept traffic.

## Tests

`tests/test_migrations.py` runs against a **real MySQL server** and is gated
on an environment variable pointing at a *disposable* database:

```bash
# Windows PowerShell
$env:MIGRATION_TEST_DATABASE_URL='mysql+pymysql://root:PASS@localhost:3306/scholaris_migrate'
python -m pytest tests/test_migrations.py -v
```

Without the variable the tests skip (the default suite stays SQLite-only).

What is covered:

1. **Fresh upgrade** — `upgrade head` produces exactly `Base.metadata.tables`
   (+ `alembic_version`), stamped at head.
2. **Cycle** — `upgrade → downgrade base → upgrade` is stable.
3. **Legacy import** — `schemadeploy.sql` is imported, a marker row is added,
   then upgraded in place: data survives, auth columns and `refresh_tokens`
   appear, version lands on head.
4. **Drift** — `alembic check` returns 0 (models == migrations).

CI runs all four on every push using a MySQL 8.4 service container
(`.github/workflows/ci.yml`).

## Rollback guidance

* Development: `alembic downgrade base|<revision>` freely.
* Production: prefer **forward fixes** (a new corrective revision). A downgrade
  is acceptable only after (a) taking a backup (see `docs/BACKUPS.md`) and
  (b) confirming the downgrade script does not drop data-bearing tables.
