import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fdrsetu.main")

from app.core.seed import init_db
from app.lifecycle.scheduler import start_lifecycle_scheduler, shutdown_lifecycle_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure required storage directories exist
    logger.info("Initializing FDRSetu Backend...")
    for dir_path in [settings.STORAGE_DIR, settings.UPLOAD_DIR, settings.TEMP_DIR]:
        os.makedirs(dir_path, exist_ok=True)
    logger.info(f"Storage directories initialized at: {settings.STORAGE_DIR}")
    
    # Initialize DB tables and seed data
    try:
        init_db()
        logger.info("Database schemas and seed data ready.")
    except Exception as e:
        logger.error(f"Database initialization warning: {e}")

    # Start APScheduler for maturity and validity monitoring
    try:
        start_lifecycle_scheduler()
    except Exception as se:
        logger.warning(f"Could not start background scheduler: {se}")
        
    yield
    # Shutdown
    shutdown_lifecycle_scheduler()
    logger.info("FDRSetu Backend shutting down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FDRSetu – Intelligent Security Deposit and FDR Management System for AICTE",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "description": "AICTE Intelligent Security Deposit and FDR Management System",
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health",
        "status": "online"
    }
