# Deployment

## Start command

Production start (Linux containers / Railway / any Procfile-style platform):

```bash
cd backend-python
./start.sh
```

`start.sh` does two things **in this order**:

1. `alembic upgrade head` — migrations run exactly once, before any worker
   exists (no races, no import-time DDL).
2. `exec gunicorn -c gunicorn_conf.py main:app` — serves the API.

There is **no `--reload`** and no debug flag anywhere in the production path.
On Windows development machines gunicorn cannot fork; use:

```powershell
python -m uvicorn main:app --workers 2 --port 8000
```

(after running `alembic upgrade head` manually).

## Configuration (environment variables)

All configuration is environment-driven; `.env.example` lists **names only**.
The ones that matter for deployment:

| Variable | Meaning | Default |
|---|---|---|
| `DATABASE_URL` | `mysql+pymysql://USER:PASS@HOST:3306/DB` | required |
| `SECRET_KEY` | JWT signing key, ≥32 random chars. Rotating invalidates all sessions | required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | access token lifetime | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | refresh token / session lifetime | `14` |
| `ALLOWED_ORIGINS` | comma-separated exact origins (no wildcards) | empty |
| `ALLOWED_ORIGIN_PATTERNS` | comma-separated fnmatch patterns (e.g. `https://*-git-*.vercel.app`) | empty |
| `WEB_CONCURRENCY` | gunicorn workers | `4` |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | SQLAlchemy pool per worker | `5` / `10` |
| `LOG_FORMAT` / `LOG_LEVEL` | `json`/`text`, `info`/... | `json`/`info` |
| `RATE_LIMIT_ENABLED` | slowapi per-IP limits (account lockout is separate) | `true` |
| `PORT` | bind port (Railway injects this) | `8000` |

## Database connection pool sizing

Each worker process owns its own pool. Keep

```
WEB_CONCURRENCY * (DB_POOL_SIZE + DB_MAX_OVERFLOW)  <  MySQL max_connections
```

Example (defaults): `4 * (5 + 10) = 60` — fine for MySQL's default 151.
Raise `max_connections` or lower the pool before raising workers.

## CORS

* Allowed origins come **only** from `ALLOWED_ORIGINS` (exact) and
* `ALLOWED_ORIGIN_PATTERNS` (fnmatch → regex fullmatch, compiled once at
  startup — Starlette ≥1.0 removed `allow_origin_patterns`).
* `*` is never used. There is no `/debug/cors` endpoint in production builds.

## Health endpoints

| Endpoint | Purpose | Behaviour |
|---|---|---|
| `GET /health` | **Liveness** — is the process up? | always `200`, no DB access |
| `GET /ready` | **Readiness** — can it serve traffic? | `200` when the DB answers, **`503`** otherwise |

Point platform health checks at `/health` and traffic/readiness probes at
`/ready`.

## Logging

* Structured JSON to stdout (`LOG_FORMAT=json`), one line per request with a
  `request_id`, method, path, status and duration.
* Request IDs are also returned in the `X-Request-ID` response header.
* Secrets (passwords, tokens, `Authorization` headers) are never logged.

## Security headers

* API responses: no `Server` header (gunicorn `servername = None`).
* Frontend (`frontend/vercel.json`): `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`, `Strict-Transport-Security` — chosen
  so they do not break React/Vite/PWA (no CSP that blocks Vite's inline styles
  or the service worker).

## Platform notes

* **Railway**: `railway.json` → build runs `pip install -r
  requirements.txt`; start command `bash start.sh` (migrations first).
* **Vercel (frontend)**: static build (`vite build`); API base URL comes from
  `VITE_API_BASE_URL` at build time. Security headers in `frontend/vercel.json`.
* **Multiple replicas**: run migrations **once** before rolling workers —
  `start.sh` is safe when a single release runner executes first; if the
  platform starts N replicas simultaneously, add a release-phase/manual step
  `alembic upgrade head` and keep it in `start.sh` (Alembic's version table
  makes re-runs no-ops, but avoids concurrent DDL).

## Post-deploy verification

```bash
curl -fsS $API/health          # 200
curl -fsS $API/ready           # 200 (503 if DB unreachable)
curl -fsS -X OPTIONS $API/api/v1/grades -H "Origin: https://your.app" \
     -H "Access-Control-Request-Method: GET"   # allowed origin echoed, no *
```
