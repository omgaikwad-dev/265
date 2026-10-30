from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.ocr import OCRExtractionOut, OCRCorrectionRequest
from app.schemas.fdr import FDROut
from app.ocr.service import OCRService

router = APIRouter()

@router.post("/{fdr_id}/extract", response_model=OCRExtractionOut)
def trigger_ocr_extraction(
    fdr_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes AI-powered document intelligence and OCR text extraction on the FDR's uploaded instrument.
    Calculates field-level confidence scores and stores extraction results.
    """
    client_ip = request.client.host if request.client else None
    return OCRService.process_fdr_document(db, fdr_id, current_user, client_ip)

@router.get("/{fdr_id}/extraction", response_model=Optional[OCRExtractionOut])
def get_ocr_extraction(
    fdr_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves OCR extraction results, raw text, and field-level confidence scores for an FDR.
    """
    extraction = OCRService.get_extraction_by_fdr_id(db, fdr_id, current_user)
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No OCR extraction on record for this FDR. Trigger extraction via POST /{fdr_id}/extract"
        )
    return extraction

@router.patch("/{fdr_id}/extraction", response_model=FDROut)
def review_and_correct_ocr(
    fdr_id: int,
    correction: OCRCorrectionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allows human review and correction of draft OCR-extracted fields before final submission.
    Directly updates FDR attributes and records audit log.
    """
    client_ip = request.client.host if request.client else None
    return OCRService.apply_reviewed_corrections(
        db, fdr_id, correction.corrected_fields, current_user, client_ip
    )

