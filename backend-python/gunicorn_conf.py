"""Gunicorn configuration for SCHOLARIS.

Every value is environment-driven so the same image can be promoted between
environments without code changes.  There is deliberately NO ``--reload`` and
no debug flag anywhere in the production path.

Sizing rule of thumb (see docs/DEPLOYMENT.md):

    total_db_connections ~= WEB_CONCURRENCY * DB_POOL_MAX

Keep that product below MySQL's ``max_connections``.
"""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Number of application workers.  4 is the documented default for a
# 1,000-1,500 student deployment; override per environment.
workers = int(os.environ.get("WEB_CONCURRENCY", "4"))

worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "uvicorn.workers.UvicornWorker")

# Requests that take longer than this are killed (seconds).
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "60"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

# Access/error logs to stdout/stderr so the platform captures them.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
access_log_format = os.environ.get(
    "GUNICORN_ACCESS_FORMAT",
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
)

# Do not forward the Server header - remove a free fingerprint.
servername = None

# Reap worker memory growth before it forces an OOM kill.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "100"))
