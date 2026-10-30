from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.fdr import FDRDocument
from app.schemas.fdr import FDRDocumentOut
from app.services.document_service import DocumentService

router = APIRouter()

@router.post("/upload", response_model=FDRDocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_standalone_document(
    file: UploadFile = File(...),
    document_type: str = Form("FDR_INSTRUMENT"),
    institution_id: int = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads a standalone document for preview / OCR staging.
    Enforces that institution users can only upload for their own institution.
    """
    user_role = current_user.role.name if current_user.role else None
    if user_role == "ROLE_INSTITUTION_ADMIN":
        target_inst_id = current_user.institution_id
    else:
        target_inst_id = institution_id or current_user.institution_id

    if not target_inst_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Institution ID is required for document upload"
        )

    return await DocumentService.save_uploaded_document(
        db=db,
        upload_file=file,
        institution_id=target_inst_id,
        uploaded_by_user=current_user,
        document_type=document_type
    )

@router.get("/{document_id}", response_model=FDRDocumentOut)
def get_document_metadata(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves document metadata (filename, hash, size, type).
    """
    doc = db.query(FDRDocument).filter(FDRDocument.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    user_role = current_user.role.name if current_user.role else None
    if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != doc.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to document from another institution"
        )
    return doc

@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Authorized document download endpoint.
    Streams file securely without exposing private filesystem paths publicly.
    """
    file_path, filename, mime_type = DocumentService.get_document_for_download(
        db=db,
        document_id=document_id,
        current_user=current_user
    )
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/{document_id}/preview")
def preview_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Authorized document inline preview endpoint for PDF / image viewer.
    """
    file_path, filename, mime_type = DocumentService.get_document_for_download(
        db=db,
        document_id=document_id,
        current_user=current_user
    )
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes an uploaded document, subject to statutory retention restrictions.
    """
    DocumentService.delete_document(db, document_id, current_user)
    return {"status": "success", "message": f"Document {document_id} deleted successfully"}
