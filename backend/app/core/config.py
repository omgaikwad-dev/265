import os
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="allow")
    
    PROJECT_NAME: str = "FDRSetu"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "fdrsetu-super-secret-development-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours for dev
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    # Standard PostgreSQL URI format with psycopg3: postgresql+psycopg://user:pass@host:port/dbname
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+psycopg://postgres:postgres@localhost:5432/fdrsetu_db"
    )
    
    # Fallback to local SQLite if PostgreSQL is not available in local dev environment
    USE_SQLITE_FALLBACK: bool = True
    SQLITE_URL: str = "sqlite:///./fdrsetu.db"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    
    # Storage
    STORAGE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../storage"))
    UPLOAD_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../storage/uploads"))
    TEMP_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../storage/temp"))
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png"]

settings = Settings()
