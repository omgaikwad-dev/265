import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.fdr import FDRRecord, FDRDocument
from app.models.ocr import OCRExtraction
from app.models.user import User
from app.ocr.engine import OCREngine
from app.ocr.extractor import FieldExtractor
from app.audit.service import AuditService

class OCRService:
    @staticmethod
    def process_fdr_document(
        db: Session,
        fdr_id: int,
        current_user: User,
        client_ip: Optional[str] = None
    ) -> OCRExtraction:
        """
        Executes the end-to-end OCR and document intelligence extraction workflow:
        1. Retrieves FDR instrument and attached document file.
        2. Executes PyMuPDF/OpenCV/Tesseract pipeline to extract raw text and word confidences.
        3. Parses structured financial attributes and computes field-level confidence scores.
        4. Persists results in ocr_extractions table and updates FDR status.
        """
        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FDR record {fdr_id} not found"
            )

        # Enforce multi-tenant access control
        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != fdr.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot process document belonging to another institution"
            )

        if not fdr.documents or len(fdr.documents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No documents attached to this FDR. Upload a scanned instrument copy first."
            )

        # Process the primary instrument document
        doc = fdr.documents[0]
        full_path = os.path.join(settings.STORAGE_DIR, doc.file_path)
        if not os.path.exists(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Underlying document file missing from storage repository"
            )

        # Update status
        fdr.ocr_status = "PROCESSING"
        db.commit()

        start_time = time.time()
        try:
            # 1. OCR Engine Execution
            raw_text, avg_conf, tokens, engine_name = OCREngine.extract_text_and_confidence(
                file_path=full_path,
                mime_type=doc.mime_type
            )

            # 2. Intelligent Field Parsing & Confidence Scoring
            fields, confidences = FieldExtractor.extract_structured_fields(
                raw_text=raw_text,
                base_confidence=avg_conf
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Calculate overall confidence
            non_zero_confs = [c for c in confidences.values() if c > 0]
            overall_conf = round(sum(non_zero_confs) / len(non_zero_confs), 1) if non_zero_confs else 75.0

            # 3. Persist Extraction Result
            existing_extraction = db.query(OCRExtraction).filter(OCRExtraction.fdr_id == fdr.id).first()
            if existing_extraction:
                existing_extraction.raw_text = raw_text
                existing_extraction.extracted_fields = fields
                existing_extraction.field_confidences = confidences
                existing_extraction.overall_confidence = overall_conf
                existing_extraction.processing_engine = engine_name
                existing_extraction.processing_time_ms = elapsed_ms
                extraction_record = existing_extraction
            else:
                extraction_record = OCRExtraction(
                    fdr_id=fdr.id,
                    document_id=doc.id,
                    raw_text=raw_text,
                    extracted_fields=fields,
                    field_confidences=confidences,
                    overall_confidence=overall_conf,
                    processing_engine=engine_name,
                    processing_time_ms=elapsed_ms
                )
                db.add(extraction_record)

            fdr.ocr_status = "COMPLETED"
            db.commit()
            db.refresh(extraction_record)

            # Audit log
            AuditService.log_event(
                db=db,
                action="OCR_PROCESSING_COMPLETED",
                entity_type="FDR_OCR",
                entity_id=str(fdr.id),
                user_id=current_user.id,
                username=current_user.username,
                role=user_role,
                details=f"OCR extracted {len(fields)} fields with overall confidence {overall_conf}% in {elapsed_ms}ms",
                ip_address=client_ip
            )

            return extraction_record

        except Exception as e:
            fdr.ocr_status = "FAILED"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OCR processing failed: {str(e)}"
            )

    @staticmethod
    def get_extraction_by_fdr_id(
        db: Session,
        fdr_id: int,
        current_user: User
    ) -> Optional[OCRExtraction]:
        """Retrieves OCR extraction result for an FDR record."""
        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FDR record not found"
            )

        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != fdr.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot access OCR record belonging to another institution"
            )

        return db.query(OCRExtraction).filter(OCRExtraction.fdr_id == fdr_id).first()

    @staticmethod
    def apply_reviewed_corrections(
        db: Session,
        fdr_id: int,
        corrected_fields: Dict[str, Any],
        current_user: User,
        client_ip: Optional[str] = None
    ) -> FDRRecord:
        """
        Allows authorized user to review and correct draft extracted fields,
        applying verified values directly onto the target FDR record.
        """
        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FDR record not found")

        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != fdr.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        extraction = db.query(OCRExtraction).filter(OCRExtraction.fdr_id == fdr_id).first()
        if extraction:
            extraction.extracted_fields = {**extraction.extracted_fields, **corrected_fields}
            conf_update = dict(extraction.field_confidences or {})
            for k in corrected_fields:
                conf_update[k] = 100.0
            extraction.field_confidences = conf_update
            extraction.is_reviewed = 1
            extraction.reviewed_by_id = current_user.id
            extraction.reviewed_at = datetime.now(timezone.utc)

        # Apply onto FDR record
        if "fdr_number" in corrected_fields and corrected_fields["fdr_number"]:
            fdr.fdr_number = str(corrected_fields["fdr_number"]).strip()
        if "bank_name" in corrected_fields and corrected_fields["bank_name"]:
            fdr.bank_name = str(corrected_fields["bank_name"]).strip()
        if "branch_name" in corrected_fields and corrected_fields["branch_name"]:
            fdr.branch_name = str(corrected_fields["branch_name"]).strip()
        if "ifsc_code" in corrected_fields and corrected_fields["ifsc_code"]:
            fdr.ifsc_code = str(corrected_fields["ifsc_code"]).strip().upper()
        if "deposit_amount" in corrected_fields and corrected_fields["deposit_amount"]:
            fdr.deposit_amount = float(corrected_fields["deposit_amount"])
        if "issue_date" in corrected_fields and corrected_fields["issue_date"]:
            fdr.issue_date = datetime.strptime(str(corrected_fields["issue_date"])[:10], "%Y-%m-%d").date()
        if "maturity_date" in corrected_fields and corrected_fields["maturity_date"]:
            fdr.maturity_date = datetime.strptime(str(corrected_fields["maturity_date"])[:10], "%Y-%m-%d").date()
        if "interest_rate" in corrected_fields and corrected_fields["interest_rate"] is not None:
            fdr.interest_rate = float(corrected_fields["interest_rate"])

        fdr.ocr_status = "OCR_REVIEWED"
        db.commit()
        db.refresh(fdr)

        AuditService.log_event(
            db=db,
            action="OCR_FIELDS_REVIEWED_AND_APPLIED",
            entity_type="FDR",
            entity_id=str(fdr.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            details=f"Human review and field correction applied to FDR {fdr.fdr_number}",
            ip_address=client_ip
        )

        return fdr
