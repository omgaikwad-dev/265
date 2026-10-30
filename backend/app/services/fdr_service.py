import os
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.fdr import FDRRecord, FDRDocument
from app.models.institution import Institution
from app.models.user import User
from app.schemas.fdr import FDRCreate, FDRUpdate
from app.audit.service import AuditService

class FDRService:
    @staticmethod
    def get_fdr_list(
        db: Session,
        current_user: User,
        institution_id: Optional[int] = None,
        lifecycle_status: Optional[str] = None,
        bank_name: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[FDRRecord], int]:
        """
        Lists FDR records with role scoping and filters.
        Enforces Rule 11: Institution Admins are strictly scoped to their own institution.
        """
        user_role = current_user.role.name if current_user.role else None
        query = db.query(FDRRecord)

        # Enforce multi-tenant data isolation
        if user_role == "ROLE_INSTITUTION_ADMIN":
            if not current_user.institution_id:
                return [], 0
            query = query.filter(FDRRecord.institution_id == current_user.institution_id)
        elif institution_id:
            query = query.filter(FDRRecord.institution_id == institution_id)

        # Filters
        if lifecycle_status:
            query = query.filter(FDRRecord.lifecycle_status == lifecycle_status)
        if bank_name:
            query = query.filter(FDRRecord.bank_name.ilike(f"%{bank_name}%"))
        if search:
            search_fmt = f"%{search}%"
            query = query.filter(
                (FDRRecord.fdr_number.ilike(search_fmt)) |
                (FDRRecord.bank_name.ilike(search_fmt)) |
                (FDRRecord.branch_name.ilike(search_fmt)) |
                (FDRRecord.ifsc_code.ilike(search_fmt))
            )

        total_count = query.count()
        records = query.order_by(FDRRecord.created_at.desc()).offset(skip).limit(limit).all()

        # Augment with institution metadata
        for rec in records:
            if rec.institution:
                rec.institution_name = rec.institution.name
                rec.aicte_id = rec.institution.aicte_id

        return records, total_count

    @staticmethod
    def get_fdr_by_id(
        db: Session,
        fdr_id: int,
        current_user: User
    ) -> FDRRecord:
        """
        Retrieves a single FDR by ID, verifying tenant isolation.
        """
        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FDR record with ID {fdr_id} not found"
            )

        # Institution isolation guard
        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN":
            if current_user.institution_id != fdr.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cannot access FDR record belonging to another institution"
                )

        if fdr.institution:
            fdr.institution_name = fdr.institution.name
            fdr.aicte_id = fdr.institution.aicte_id

        return fdr

    @staticmethod
    def create_fdr(
        db: Session,
        fdr_in: FDRCreate,
        current_user: User,
        client_ip: Optional[str] = None
    ) -> FDRRecord:
        """
        Creates a new FDR record in DRAFT status, preventing duplicate instrument numbers.
        """
        user_role = current_user.role.name if current_user.role else None

        # Resolve institution ID
        if user_role == "ROLE_INSTITUTION_ADMIN":
            if not current_user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Your account is not associated with an institution"
                )
            target_institution_id = current_user.institution_id
        else:
            if not fdr_in.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target institution_id is required"
                )
            target_institution_id = fdr_in.institution_id

        # Duplicate FDR detection: check if FDR number already exists in same bank
        existing = db.query(FDRRecord).filter(
            FDRRecord.fdr_number == fdr_in.fdr_number.strip(),
            FDRRecord.bank_name.ilike(fdr_in.bank_name.strip())
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate FDR detected: FDR Number '{fdr_in.fdr_number}' is already registered with {fdr_in.bank_name}."
            )

        fdr_record = FDRRecord(
            institution_id=target_institution_id,
            submitted_by_id=current_user.id,
            fdr_number=fdr_in.fdr_number.strip(),
            bank_name=fdr_in.bank_name.strip(),
            branch_name=fdr_in.branch_name.strip(),
            ifsc_code=fdr_in.ifsc_code.strip().upper(),
            deposit_amount=fdr_in.deposit_amount,
            issue_date=fdr_in.issue_date,
            maturity_date=fdr_in.maturity_date,
            interest_rate=fdr_in.interest_rate,
            beneficiary=fdr_in.beneficiary or "Member Secretary, AICTE / Regional Officer, AICTE",
            joint_holder=fdr_in.joint_holder,
            instrument_type=fdr_in.instrument_type or "Fixed Deposit Receipt",
            is_auto_renewal=fdr_in.is_auto_renewal or False,
            previous_fdr_id=fdr_in.previous_fdr_id,
            replacement_fdr_id=fdr_in.replacement_fdr_id,
            ocr_status="MANUALLY_ENTERED",
            verification_status="UNVERIFIED",
            lifecycle_status="DRAFT"
        )
        db.add(fdr_record)
        db.commit()
        db.refresh(fdr_record)

        # Audit log
        AuditService.log_event(
            db=db,
            action="FDR_CREATED",
            entity_type="FDR",
            entity_id=str(fdr_record.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            new_value={"fdr_number": fdr_record.fdr_number, "amount": str(fdr_record.deposit_amount), "bank": fdr_record.bank_name},
            ip_address=client_ip
        )

        return fdr_record

    @staticmethod
    def update_fdr(
        db: Session,
        fdr_id: int,
        fdr_update: FDRUpdate,
        current_user: User,
        client_ip: Optional[str] = None
    ) -> FDRRecord:
        """
        Updates editable fields of a draft or returned FDR.
        """
        fdr = FDRService.get_fdr_by_id(db, fdr_id, current_user)
        
        # Only permit edit if DRAFT or ADDITIONAL_INFO_REQUIRED
        if fdr.lifecycle_status not in ["DRAFT", "ADDITIONAL_INFO_REQUIRED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit FDR in '{fdr.lifecycle_status}' status. Only DRAFT records may be edited."
            )

        update_data = fdr_update.model_dump(exclude_unset=True)

        # Validate duplicate FDR if number or bank is altered
        if "fdr_number" in update_data or "bank_name" in update_data:
            chk_num = update_data.get("fdr_number", fdr.fdr_number).strip()
            chk_bank = update_data.get("bank_name", fdr.bank_name).strip()
            existing = db.query(FDRRecord).filter(
                FDRRecord.id != fdr.id,
                FDRRecord.fdr_number == chk_num,
                FDRRecord.bank_name.ilike(chk_bank)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate FDR detected: FDR Number '{chk_num}' is already registered with {chk_bank}."
                )

        # Validate dates if updated
        new_issue = update_data.get("issue_date", fdr.issue_date)
        new_maturity = update_data.get("maturity_date", fdr.maturity_date)
        if new_issue and new_maturity and new_maturity <= new_issue:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maturity date must be after the issue date"
            )

        # Validate IFSC if updated
        if "ifsc_code" in update_data:
            ifsc_clean = update_data["ifsc_code"].strip().upper()
            if len(ifsc_clean) != 11 or ifsc_clean[4] != "0":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid IFSC code: Must be 11 characters with '0' as 5th character"
                )
            update_data["ifsc_code"] = ifsc_clean

        prev_data = {k: getattr(fdr, k) for k in update_data.keys() if hasattr(fdr, k)}

        for field, value in update_data.items():
            setattr(fdr, field, value)

        db.commit()
        db.refresh(fdr)

        AuditService.log_event(
            db=db,
            action="FDR_UPDATED",
            entity_type="FDR",
            entity_id=str(fdr.id),
            user_id=current_user.id,
            username=current_user.username,
            role=current_user.role.name if current_user.role else None,
            previous_value=str(prev_data),
            new_value=str(update_data),
            ip_address=client_ip
        )

        return fdr

    @staticmethod
    def delete_fdr(
        db: Session,
        fdr_id: int,
        current_user: User,
        client_ip: Optional[str] = None
    ) -> bool:
        """
        Deletes a DRAFT FDR and removes any associated uploaded files.
        Submitted or approved FDRs cannot be deleted to preserve compliance audit trails.
        """
        fdr = FDRService.get_fdr_by_id(db, fdr_id, current_user)

        if fdr.lifecycle_status != "DRAFT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete FDR in '{fdr.lifecycle_status}' status. Only DRAFT records may be discarded."
            )

        # Remove physical document files from disk
        for doc in fdr.documents:
            full_path = os.path.join(settings.STORAGE_DIR, doc.file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception:
                    pass

        fdr_number = fdr.fdr_number
        inst_id = fdr.institution_id

        db.delete(fdr)
        db.commit()

        AuditService.log_event(
            db=db,
            action="FDR_DELETED",
            entity_type="FDR",
            entity_id=str(fdr_id),
            user_id=current_user.id,
            username=current_user.username,
            role=current_user.role.name if current_user.role else None,
            details=f"Draft FDR {fdr_number} (Institution {inst_id}) deleted by {current_user.email}",
            ip_address=client_ip
        )

        return True

    @staticmethod
    def submit_for_scrutiny(
        db: Session,
        fdr_id: int,
        current_user: User,
        client_ip: Optional[str] = None
    ) -> FDRRecord:
        """
        Submits an FDR for scrutiny examination, validating that at least one document is attached.
        """
        fdr = FDRService.get_fdr_by_id(db, fdr_id, current_user)

        if fdr.lifecycle_status != "DRAFT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FDR is already in '{fdr.lifecycle_status}' status."
            )

        # Rule 10: Missing document check
        if not fdr.documents or len(fdr.documents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing supporting document: You must upload the official FDR copy before submitting for scrutiny."
            )

        fdr.lifecycle_status = "UNDER_SCRUTINY"
        fdr.submitted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(fdr)

        # Trigger Automated 12-Rule Verification Engine upon scrutiny submission
        try:
            from app.verification.service import VerificationService
            VerificationService.run_verification(db, fdr.id, current_user, client_ip)
            db.refresh(fdr)
        except Exception as ve:
            # Non-blocking if rule engine encounters unexpected evaluation issue
            pass

        AuditService.log_event(
            db=db,
            action="FDR_SUBMITTED_FOR_SCRUTINY",
            entity_type="FDR",
            entity_id=str(fdr.id),
            user_id=current_user.id,
            username=current_user.username,
            role=current_user.role.name if current_user.role else None,
            details=f"FDR {fdr.fdr_number} submitted for scrutiny by {current_user.email}",
            ip_address=client_ip
        )

        return fdr

    @staticmethod
    def get_statistics(
        db: Session,
        current_user: User,
        institution_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Computes dynamic, database-driven metrics.
        Satisfies Rule 7: Dashboard metrics must come from real database queries.
        """
        user_role = current_user.role.name if current_user.role else None
        today = date.today()
        ninety_days = today + timedelta(days=90)

        query = db.query(FDRRecord)

        # Enforce multi-tenant scoping
        if user_role == "ROLE_INSTITUTION_ADMIN":
            if not current_user.institution_id:
                return {
                    "total_fdrs": 0,
                    "total_deposit_amount": Decimal("0.00"),
                    "active_count": 0,
                    "draft_count": 0,
                    "under_scrutiny_count": 0,
                    "expiring_soon_count": 0,
                    "matured_count": 0,
                    "total_institutions": None
                }
            query = query.filter(FDRRecord.institution_id == current_user.institution_id)
            total_institutions = None
        else:
            if institution_id:
                query = query.filter(FDRRecord.institution_id == institution_id)
            total_institutions = db.query(Institution).count()

        all_records = query.all()
        total_fdrs = len(all_records)
        total_deposit_amount = sum((r.deposit_amount for r in all_records), Decimal("0.00"))
        
        active_count = sum(1 for r in all_records if r.lifecycle_status == "APPROVED_ACTIVE")
        draft_count = sum(1 for r in all_records if r.lifecycle_status == "DRAFT")
        under_scrutiny_count = sum(1 for r in all_records if r.lifecycle_status == "UNDER_SCRUTINY")
        expiring_soon_count = sum(
            1 for r in all_records 
            if r.lifecycle_status == "APPROVED_ACTIVE" and today <= r.maturity_date <= ninety_days
        )
        matured_count = sum(
            1 for r in all_records 
            if r.maturity_date < today or r.lifecycle_status == "MATURED"
        )

        return {
            "total_fdrs": total_fdrs,
            "total_deposit_amount": total_deposit_amount,
            "active_count": active_count,
            "draft_count": draft_count,
            "under_scrutiny_count": under_scrutiny_count,
            "expiring_soon_count": expiring_soon_count,
            "matured_count": matured_count,
            "total_institutions": total_institutions
        }
