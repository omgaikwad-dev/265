import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("fdrsetu.database")

Base = declarative_base()

def get_engine():
    db_url = settings.DATABASE_URL
    try:
        # Try primary database (PostgreSQL)
        eng = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3} if "postgresql" in db_url else {}
        )
        # Test connection
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Connected to primary database: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        return eng, "postgresql"
    except Exception as e:
        if settings.USE_SQLITE_FALLBACK:
            logger.warning(f"Could not connect to PostgreSQL ({e}). Falling back to SQLite for local development: {settings.SQLITE_URL}")
            fallback_eng = create_engine(
                settings.SQLITE_URL,
                connect_args={"check_same_thread": False}
            )
            return fallback_eng, "sqlite"
        raise e

engine, active_db_dialect = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_database_connection() -> dict:
    """Verifies database connectivity and returns status metadata."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            return {
                "status": "connected",
                "dialect": active_db_dialect,
                "verified": result == 1
            }
    except Exception as exc:
        return {
            "status": "disconnected",
            "dialect": active_db_dialect,
            "error": str(exc),
            "verified": False
        }
