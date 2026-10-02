# Backups & Restore

Backups protect **data**, not schema. Schema always comes from Alembic
(`alembic upgrade head` — see `MIGRATIONS.md`); restoring an old dump into a
new deploy upgrades it in place.

## What to back up

1. **MySQL database** (the only source of truth for school data).
2. **`backend-python/media/`** — user-uploaded files (profile photos); the
   directory is git-ignored and lives only on the host/volume.
3. **Secrets** — `SECRET_KEY` and platform env vars (store in the platform's
   secret manager, not in the backup set).

## Taking a backup

Consistent online backup (InnoDB, no downtime):

```bash
mysqldump \
  --host=DB_HOST --user=DB_USER --password \
  --single-transaction --routines --triggers \
  --set-gtid-purged=OFF \
  DB_NAME > "scholaris_$(date +%Y%m%d_%H%M%S).sql"
```

Compressed (recommended for scheduled jobs):

```bash
mysqldump --single-transaction --set-gtid-purged=OFF \
  --host=DB_HOST --user=DB_USER --password DB_NAME \
  | gzip > "scholaris_$(date +%Y%m%d_%H%M%S).sql.gz"
```

### Schedule

* **Daily** full dump, retained 14 days.
* **Weekly** dump, retained 8 weeks.
* Keep at least one copy **off the database host** (object storage / another
  machine). A backup on the same disk as the DB survives almost nothing.

Example cron (daily 02:00):

```cron
0 2 * * * mysqldump --single-transaction --set-gtid-purged=OFF \
  --host=localhost --user=scholaris --password \
  scholaris | gzip > /backups/scholaris_$(date +\%Y\%m\%d).sql.gz
```

On managed platforms (Railway, RDS, ...) enable the managed PITR/snapshot
feature *in addition to* logical dumps.

## Restoring

```bash
# 1. Restore the dump into a scratch database first — always verify there.
mysql --host=DB_HOST --user=DB_USER --password \
  -e "CREATE DATABASE scholaris_restore CHARACTER SET utf8mb4"
gunzip -c backup.sql.gz | mysql --host=DB_HOST --user=DB_USER --password \
  scholaris_restore

# 2. Bring the schema to current (legacy dumps upgrade in place).
cd backend-python
DATABASE_URL=mysql+pymysql://USER:PASS@HOST:3306/scholaris_restore \
  alembic upgrade head

# 3. Sanity checks.
mysql ... -e "SELECT COUNT(*) FROM schools; SELECT COUNT(*) FROM users; \
  SELECT version_num FROM scholaris_restore.alembic_version;"
```

Only after the scratch restore looks right, repeat against the real database
(with the application stopped, or accept the write window).

## Verifying backups (do this, don't just take them)

* **Monthly**: restore the newest dump into a scratch DB and run
  `alembic upgrade head` + a smoke login against it.
* Check file age and size of every scheduled backup (alert if > 25 hours old).
* After any restore drill, record the elapsed restore time — that is your
  real RTO.

## What backups do NOT replace

* Schema migrations (Alembic) — restores start from dump schema.
* `media/` files — they are not in the SQL dump; rsync/snapshot that
  directory separately.
* Secret rotation — if `SECRET_KEY` leaks, rotate it (all sessions expire);
  keeping an old copy of `.env` in a backup does not fix a leak.
