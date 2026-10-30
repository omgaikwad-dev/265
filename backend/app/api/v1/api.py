from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, institution, fdr, document, ocr, verification

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health & System"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Access"])
api_router.include_router(institution.router, prefix="/institutions", tags=["Institution Management"])
api_router.include_router(fdr.router, prefix="/fdr", tags=["FDR Management"])
api_router.include_router(document.router, prefix="/documents", tags=["Document Management"])
api_router.include_router(ocr.router, prefix="/fdr", tags=["OCR Document Intelligence"])
api_router.include_router(verification.router, tags=["Verification & Scrutiny Engine"])

