import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(
            f"Environment variable {name} must be an integer, got: {raw!r}"
        )


database_url = settings.DATABASE_URL

if database_url.startswith("mysql://"):
    database_url = database_url.replace(
        "mysql://",
        "mysql+pymysql://",
        1,
    )

# Connection-pool sizing is environment-driven because the correct value
# depends on the number of gunicorn workers:
#
#     total_connections ~= WEB_CONCURRENCY * (DB_POOL_SIZE + DB_MAX_OVERFLOW)
#
# Keep that product comfortably below MySQL's max_connections
# (default 151; Railway plans vary).  See docs/DEPLOYMENT.md.
_POOL_SIZE = _int_env("DB_POOL_SIZE", 5)
_MAX_OVERFLOW = _int_env("DB_MAX_OVERFLOW", 10)
_POOL_TIMEOUT = _int_env("DB_POOL_TIMEOUT", 30)
_POOL_RECYCLE = _int_env("DB_POOL_RECYCLE", 1800)

if database_url.startswith("sqlite"):
    # SQLite (tests / local smoke runs): file-backed, no pooling semantics,
    # and SQLAlchemy's QueuePool would try to hand out connections with
    # pre-ping options SQLite rejects.
    engine = create_engine(
        database_url,
        echo=False,
    )
else:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=_POOL_SIZE,
        max_overflow=_MAX_OVERFLOW,
        pool_timeout=_POOL_TIMEOUT,
        pool_recycle=_POOL_RECYCLE,
        echo=False,
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
