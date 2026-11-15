"""Database engine, connection pooling, session factory, and health verification."""

import logging
import time
from contextlib import contextmanager
from typing import Dict, Any, Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""
    pass


def build_engine(database_url: str | None = None) -> Engine:
    """Create SQLAlchemy Engine with production PostgreSQL connection pooling."""
    settings = get_settings()
    url = database_url or settings.DATABASE_URL

    if settings.APP_ENV.lower() == "production" and url.startswith("sqlite"):
        raise RuntimeError("SQLite is strictly disallowed in production. Use Supabase PostgreSQL.")

    if url.startswith("sqlite"):
        # Used ONLY in isolated local automated tests if explicitly configured in testing mode
        connect_args = {"check_same_thread": False}
        poolclass = StaticPool if ":memory:" in url else QueuePool
        engine = create_engine(
            url,
            connect_args=connect_args,
            poolclass=poolclass,
            echo=settings.DB_ECHO,
        )

        @event.listens_for(engine, "connect")
        def _enable_sqlite_fks(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    # Production / Development PostgreSQL (Supabase PostgreSQL)
    connect_args: Dict[str, Any] = {
        "connect_timeout": 10,
        "application_name": "exam_seating_portal_backend",
    }
    engine = create_engine(
        url,
        poolclass=QueuePool,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=settings.DB_ECHO,
        connect_args=connect_args,
    )
    return engine


engine: Engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def reconfigure_database(database_url: str) -> None:
    """Rebind global engine and SessionLocal (useful for test suites or dynamic reconfiguration)."""
    global engine, SessionLocal
    engine.dispose()
    engine = build_engine(database_url)
    SessionLocal.configure(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency providing a database session with automatic rollback on unhandled error."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def transactional_session(db: Session) -> Generator[Session, None, None]:
    """Execute a block of database operations inside an atomic transaction with automatic rollback."""
    try:
        yield db
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Database transaction rolled back due to error: %s", exc)
        raise


def verify_database_connection() -> Dict[str, Any]:
    """Execute a lightweight health query against the database and measure latency."""
    start = time.perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        dialect = engine.dialect.name
        return {
            "connected": True,
            "dialect": dialect,
            "latency_ms": latency_ms,
            "pool_status": engine.pool.status() if hasattr(engine.pool, "status") else "active",
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.error("Database health check failed: %s", exc)
        return {
            "connected": False,
            "dialect": engine.dialect.name,
            "latency_ms": latency_ms,
            "error": str(exc),
        }
