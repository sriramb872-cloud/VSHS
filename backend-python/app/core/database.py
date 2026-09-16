from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

database_url = settings.DATABASE_URL

if database_url.startswith("mysql://"):
    database_url = database_url.replace(
        "mysql://",
        "mysql+pymysql://",
        1,
    )

engine = create_engine(
    database_url,
    pool_pre_ping=True,
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

