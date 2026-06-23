import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# DATABASE_URL is env-driven for deploy. Defaults to local SQLite so dev needs
# no setup. On Railway, set it to the Postgres plugin's connection string.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./school_v4.db")

# Railway/Heroku hand out "postgres://"; SQLAlchemy 2.0 wants "postgresql://".
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # pool_pre_ping avoids stale-connection errors on managed Postgres.
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()
