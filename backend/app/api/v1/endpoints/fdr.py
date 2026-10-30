from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.fdr import FDRCreate, FDRUpdate, FDROut, FDRDocumentOut, FDRStatisticsOut
from app.services.fdr_service import FDRService
from app.services.document_service import DocumentService

router = APIRouter()

@router.get("", response_model=List[FDROut])
def list_fdrs(
    institution_id: Optional[int] = Query(None, description="Filter by institution (AICTE staff only)"),
    status: Optional[str] = Query(None, description="Filter by lifecycle status"),
    bank: Optional[str] = Query(None, description="Filter by bank name"),
    search: Optional[str] = Query(None, description="Search FDR number, bank, or branch"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List FDR records with multi-tenant isolation.
    - Institution Admins only receive records for their own institution.
    - AICTE staff / Auditors can view all or filter by institution.
    """
    records, total = FDRService.get_fdr_list(
        db=db,
        current_user=current_user,
        institution_id=institution_id,
        lifecycle_status=status,
        bank_name=bank,
        search=search,
        skip=skip,
        limit=limit
    )
    return records

@router.get("/statistics", response_model=FDRStatisticsOut)
def get_fdr_statistics(
    institution_id: Optional[int] = Query(None, description="Scope statistics to institution (AICTE staff)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes real-time dynamic statistics across FDR records.
    - Institution Admin: scoped automatically to own institution.
    - AICTE staff / Auditors: system-wide or scoped by institution.
    """
    return FDRService.get_statistics(db, current_user, institution_id)

@router.post("", response_model=FDROut, status_code=status.HTTP_201_CREATED)
def create_fdr(
    fdr_in: FDRCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new FDR record in DRAFT status.
    Guarantees no duplicate FDR number is registered with the same bank.
    """
    client_ip = request.client.host if request.client else None
    return FDRService.create_fdr(db, fdr_in, current_user, client_ip)

@router.get("/{fdr_id}", response_model=FDROut)
def get_fdr(
    fdr_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get full FDR record and attached documents.
    """
    return FDRService.get_fdr_by_id(db, fdr_id, current_user)

@router.patch("/{fdr_id}", response_model=FDROut)
def update_fdr(
    fdr_id: int,
    fdr_update: FDRUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update permitted fields of a draft FDR.
    """
    client_ip = request.client.host if request.client else None
    return FDRService.update_fdr(db, fdr_id, fdr_update, current_user, client_ip)

@router.delete("/{fdr_id}")
def delete_fdr(
    fdr_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a DRAFT FDR.
    Records that have been submitted or approved cannot be deleted.
    """
    client_ip = request.client.host if request.client else None
    FDRService.delete_fdr(db, fdr_id, current_user, client_ip)
    return {"status": "success", "message": f"Draft FDR {fdr_id} has been discarded"}

@router.post("/{fdr_id}/submit", response_model=FDROut)
def submit_fdr_for_scrutiny(
    fdr_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submits a draft FDR for scrutiny examination.
    Validates that supporting documents have been uploaded.
    """
    client_ip = request.client.host if request.client else None
    return FDRService.submit_for_scrutiny(db, fdr_id, current_user, client_ip)

@router.post("/{fdr_id}/documents", response_model=FDRDocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_fdr_document(
    fdr_id: int,
    file: UploadFile = File(...),
    document_type: str = Form("FDR_INSTRUMENT"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads a supporting document (PDF, JPG, PNG) and links it directly to an FDR.
    Validates file magic signatures and calculates SHA-256 hash.
    """
    fdr = FDRService.get_fdr_by_id(db, fdr_id, current_user)
    
    doc = await DocumentService.save_uploaded_document(
        db=db,
        upload_file=file,
        institution_id=fdr.institution_id,
        uploaded_by_user=current_user,
        document_type=document_type,
        fdr_id=fdr.id
    )
    return doc
