import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db, check_database_connection

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """
    System Health-check API endpoint.
    Checks application status, database connectivity, and storage availability.
    """
    db_health = check_database_connection()
    
    # Check storage directories
    storage_ok = True
    storage_details = {}
    for name, path in [("root", settings.STORAGE_DIR), ("uploads", settings.UPLOAD_DIR), ("temp", settings.TEMP_DIR)]:
        exists = os.path.exists(path)
        writable = os.access(path, os.W_OK) if exists else False
        storage_details[name] = {"exists": exists, "writable": writable, "path": path}
        if not exists or not writable:
            storage_ok = False
            
    is_overall_healthy = db_health.get("verified", False) and storage_ok
    
    return {
        "status": "healthy" if is_overall_healthy else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_health,
        "storage": {
            "status": "ready" if storage_ok else "attention_needed",
            "directories": storage_details
        }
    }
