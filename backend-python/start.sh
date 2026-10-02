#!/usr/bin/env bash
# SCHOLARIS backend production start command.
#
# Order matters and is the whole point of this script:
#   1. run pending Alembic migrations EXACTLY ONCE, before any worker exists;
#   2. only then hand off to gunicorn (which never runs DDL at import time).
#
# This runs as the container's main process, so `exec` makes gunicorn PID 1
# and lets it receive signals for graceful shutdown.
set -euo pipefail

cd "$(dirname "$0")"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "FATAL: DATABASE_URL is not set - refusing to start." >&2
  exit 1
fi

echo "==> Running database migrations (alembic upgrade head)"
alembic upgrade head

echo "==> Starting gunicorn"
exec gunicorn --config gunicorn_conf.py main:app
