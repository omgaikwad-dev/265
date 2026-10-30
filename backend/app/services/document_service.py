import os
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Tuple
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.fdr import FDRDocument
from app.models.user import User

MAGIC_NUMBERS = {
    "pdf": b"%PDF",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
}

class DocumentService:
    @staticmethod
    def validate_file_content(content: bytes, filename: str) -> str:
        """
        Validates file size, extension, and binary magic bytes to prevent masquerading or malicious uploads.
        Returns the confirmed MIME type.
        """
        # 1. Size check
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB",
            )
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)",
            )

        # 2. Extension check
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if f".{ext}" not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Disallowed file format '.{ext}'. Supported formats: {settings.ALLOWED_EXTENSIONS}",
            )

        # 3. Magic signature validation
        expected_sig = MAGIC_NUMBERS.get(ext)
        if ext in ["jpg", "jpeg"]:
            if not content.startswith(b"\xff\xd8\xff"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JPEG image signature. File content does not match extension.",
                )
            mime_type = "image/jpeg"
        elif ext == "png":
            if not content.startswith(b"\x89PNG\r\n\x1a\n"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid PNG image signature. File content does not match extension.",
                )
            mime_type = "image/png"
        elif ext == "pdf":
            if not content.startswith(b"%PDF"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid PDF document signature. File content does not match extension.",
                )
            mime_type = "application/pdf"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file format",
            )

        return mime_type

    @staticmethod
    async def save_uploaded_document(
        db: Session,
        upload_file: UploadFile,
        institution_id: int,
        uploaded_by_user: User,
        document_type: str = "FDR_INSTRUMENT",
        fdr_id: int = None
    ) -> FDRDocument:
        """
        Reads file, validates magic bytes, computes SHA-256 checksum, stores to private vault,
        and saves metadata in the database.
        """
        content = await upload_file.read()
        mime_type = DocumentService.validate_file_content(content, upload_file.filename)
        
        # Calculate cryptographic hash
        sha256_hash = hashlib.sha256(content).hexdigest()

        # Sanitize storage location
        year_folder = str(datetime.now(timezone.utc).year)
        dest_dir = os.path.join(settings.UPLOAD_DIR, year_folder)
        os.makedirs(dest_dir, exist_ok=True)

        ext = os.path.splitext(upload_file.filename)[1].lower()
        stored_name = f"doc_{uuid.uuid4().hex}{ext}"
        full_dest_path = os.path.join(dest_dir, stored_name)

        # Write to secure private disk location
        with open(full_dest_path, "wb") as f:
            f.write(content)

        # Relative path from project storage for portability
        rel_path = os.path.relpath(full_dest_path, settings.STORAGE_DIR)

        # Persist DB record
        doc_record = FDRDocument(
            fdr_id=fdr_id,
            institution_id=institution_id,
            uploaded_by_id=uploaded_by_user.id,
            document_type=document_type,
            original_filename=upload_file.filename,
            stored_filename=stored_name,
            file_path=rel_path,
            file_size=len(content),
            mime_type=mime_type,
            sha256_hash=sha256_hash,
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)
        return doc_record

    @staticmethod
    def get_document_for_download(
        db: Session,
        document_id: int,
        current_user: User
    ) -> Tuple[str, str, str]:
        """
        Retrieves document record, enforces role and institution access controls,
        and returns (full_absolute_path, original_filename, mime_type).
        """
        doc = db.query(FDRDocument).filter(FDRDocument.id == document_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found",
            )

        # Institution isolation check: Institution Admins can only download own documents
        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN":
            if current_user.institution_id != doc.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cannot access documents belonging to another institution",
                )

        full_path = os.path.join(settings.STORAGE_DIR, doc.file_path)
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical document file missing on storage vault",
            )

        return full_path, doc.original_filename, doc.mime_type

    @staticmethod
    def delete_document(
        db: Session,
        document_id: int,
        current_user: User
    ) -> bool:
        """
        Deletes a document only if not locked in an active/submitted scrutiny lifecycle.
        Enforces Rule 11 (tenant boundary) and document deletion restrictions.
        """
        doc = db.query(FDRDocument).filter(FDRDocument.id == document_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )

        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != doc.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to document from another institution"
            )

        # Deletion restriction: prevent deleting files from submitted FDRs
        if doc.fdr and doc.fdr.lifecycle_status != "DRAFT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document deletion restricted: Cannot remove documents from an FDR in '{doc.fdr.lifecycle_status}' status."
            )

        full_path = os.path.join(settings.STORAGE_DIR, doc.file_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception:
                pass

        db.delete(doc)
        db.commit()
        return True
