from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.fdr import FDRRecord, FDRDocument
from app.models.release import ReleaseRequest
from app.models.verification import Discrepancy
from app.models.user import User
from app.audit.service import AuditService

class ApprovalService:
    """
    Handles AICTE Approving Authority workflows, release/refund petitions,
    eligibility checks, and final statutory sign-offs.
    """

    @staticmethod
    def initiate_release_request(
        db: Session,
        fdr_id: int,
        data: Dict[str, Any],
        current_user: User,
        client_ip: Optional[str] = None
    ) -> ReleaseRequest:
        """
        Allows an institution to initiate a release / refund request for an FDR instrument.
        Validates maturity / eligibility conditions and checks for open critical discrepancies.
        """
        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FDR record not found")

        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != fdr.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Status eligibility: FDR must be active or matured or renewal due
        allowed_statuses = ["APPROVED_ACTIVE", "MATURED", "RENEWAL_DUE"]
        if fdr.lifecycle_status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot request release for FDR in '{fdr.lifecycle_status}' status. Instrument must be APPROVED_ACTIVE or MATURED."
            )

        # Check for unresolved critical/high discrepancies
        open_critical_discs = db.query(Discrepancy).filter(
            Discrepancy.fdr_id == fdr.id,
            Discrepancy.status == "OPEN",
            Discrepancy.severity.in_(["CRITICAL", "HIGH"])
        ).all()

        if open_critical_discs:
            disc_titles = [f"#{d.id}: {d.title}" for d in open_critical_discs]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot initiate release: {len(open_critical_discs)} unresolved compliance discrepancy(s) remain on record ({'; '.join(disc_titles)})."
            )

        # Create ReleaseRequest
        release_req = ReleaseRequest(
            fdr_id=fdr.id,
            institution_id=fdr.institution_id,
            requested_by_id=current_user.id,
            release_reason=data.get("release_reason", "Statutory tenure completed / Course closure"),
            refund_bank_name=data.get("refund_bank_name", fdr.bank_name),
            refund_account_number=data.get("refund_account_number", "").strip(),
            refund_ifsc=data.get("refund_ifsc", fdr.ifsc_code).strip().upper(),
            refund_beneficiary_name=data.get("refund_beneficiary_name", fdr.institution.name if fdr.institution else "Institution Account"),
            noc_document_id=data.get("noc_document_id"),
            status="PENDING"
        )
        db.add(release_req)

        # Transition FDR status
        fdr.lifecycle_status = "RELEASE_REQUESTED"

        db.commit()
        db.refresh(release_req)
        db.refresh(fdr)

        AuditService.log_event(
            db=db,
            action="FDR_RELEASE_REQUESTED",
            entity_type="RELEASE_REQUEST",
            entity_id=str(release_req.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            details=f"Release & refund petition #{release_req.id} initiated for FDR {fdr.fdr_number} (₹ {float(fdr.deposit_amount or 0):,.2f})",
            ip_address=client_ip
        )

        return release_req

    @staticmethod
    def get_fdr_release_request(
        db: Session,
        fdr_id: int,
        current_user: User
    ) -> Optional[ReleaseRequest]:
        """Returns the latest release request for an FDR."""
        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FDR not found")

        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != fdr.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return db.query(ReleaseRequest).filter(
            ReleaseRequest.fdr_id == fdr_id
        ).order_by(ReleaseRequest.created_at.desc()).first()

    @staticmethod
    def get_approval_queue(
        db: Session,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Retrieves executive approval dossiers awaiting sign-off by AICTE Approving Authority:
        1. FDR instruments under scrutiny awaiting approval/rejection.
        2. Release & refund petitions awaiting authorization.
        """
        user_role = current_user.role.name if current_user.role else None
        if user_role not in ["ROLE_APPROVING_AUTHORITY", "ROLE_SYSTEM_ADMIN", "ROLE_SCRUTINY_OFFICER", "ROLE_AUDITOR"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # 1. Scrutiny Queue (cases awaiting final statutory FDR approval)
        scrutiny_cases = db.query(FDRRecord).filter(
            FDRRecord.lifecycle_status == "UNDER_SCRUTINY"
        ).order_by(FDRRecord.submitted_at.asc()).all()

        # 2. Release Queue (petitions awaiting authorization)
        release_cases = db.query(ReleaseRequest).filter(
            ReleaseRequest.status == "PENDING"
        ).order_by(ReleaseRequest.created_at.asc()).all()

        return {
            "pending_scrutiny_fdrs": scrutiny_cases,
            "pending_releases": release_cases,
            "counts": {
                "scrutiny_pending": len(scrutiny_cases),
                "releases_pending": len(release_cases)
            }
        }

    @staticmethod
    def authority_decision_on_fdr(
        db: Session,
        fdr_id: int,
        decision: str,  # APPROVE_FDR or REJECT_FDR
        remarks: str,
        current_user: User,
        client_ip: Optional[str] = None
    ) -> FDRRecord:
        """
        AICTE Approving Authority statutory decision on an FDR submitted for scrutiny.
        """
        user_role = current_user.role.name if current_user.role else None
        if user_role not in ["ROLE_APPROVING_AUTHORITY", "ROLE_SYSTEM_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the AICTE Competent Approving Authority can grant statutory approval or rejection on FDRs"
            )

        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FDR record not found")

        now = datetime.now(timezone.utc)

        if decision == "APPROVE_FDR":
            fdr.lifecycle_status = "APPROVED_ACTIVE"
            fdr.approved_at = now
            fdr.authority_remarks = f"[APPROVED] {remarks} (Authorized by {current_user.full_name} on {now.strftime('%Y-%m-%d %H:%M UTC')})"
            action_code = "FDR_APPROVED_BY_AUTHORITY"
        elif decision == "REJECT_FDR":
            fdr.lifecycle_status = "REJECTED"
            fdr.authority_remarks = f"[REJECTED] {remarks} (Decision by {current_user.full_name} on {now.strftime('%Y-%m-%d %H:%M UTC')})"
            action_code = "FDR_REJECTED_BY_AUTHORITY"
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decision must be APPROVE_FDR or REJECT_FDR")

        db.commit()
        db.refresh(fdr)

        AuditService.log_event(
            db=db,
            action=action_code,
            entity_type="FDR",
            entity_id=str(fdr.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            details=f"Authority statutory decision '{decision}' on FDR {fdr.fdr_number}: {remarks}",
            ip_address=client_ip
        )

        return fdr

    @staticmethod
    def authority_decision_on_release(
        db: Session,
        release_id: int,
        decision: str,  # APPROVE_RELEASE or REJECT_RELEASE
        remarks: str,
        current_user: User,
        client_ip: Optional[str] = None
    ) -> ReleaseRequest:
        """
        AICTE Approving Authority statutory sign-off on an eligible release/refund petition.
        """
        user_role = current_user.role.name if current_user.role else None
        if user_role not in ["ROLE_APPROVING_AUTHORITY", "ROLE_SYSTEM_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the AICTE Competent Approving Authority can authorize release or refund of security deposits"
            )

        release_req = db.query(ReleaseRequest).filter(ReleaseRequest.id == release_id).first()
        if not release_req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release request not found")

        fdr = db.query(FDRRecord).filter(FDRRecord.id == release_req.fdr_id).first()
        if not fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated FDR not found")

        now = datetime.now(timezone.utc)
        year_str = now.strftime("%Y")

        if decision == "APPROVE_RELEASE":
            release_req.status = "APPROVED"
            auth_ref = f"AICTE/FIN/REL/{year_str}/{release_req.id:05d}"
            release_req.authorization_reference = auth_ref
            release_req.authority_remarks = remarks
            release_req.decided_by_id = current_user.id
            release_req.decided_at = now

            fdr.lifecycle_status = "RELEASED"
            fdr.authority_remarks = f"[RELEASE AUTHORIZED - Ref: {auth_ref}] {remarks}"
            action_code = "FDR_RELEASE_AUTHORIZED"

        elif decision == "REJECT_RELEASE":
            release_req.status = "REJECTED"
            release_req.authority_remarks = remarks
            release_req.decided_by_id = current_user.id
            release_req.decided_at = now

            # Return FDR to APPROVED_ACTIVE or MATURED depending on date
            days_left = (fdr.maturity_date - date.today()).days if fdr.maturity_date else 100
            fdr.lifecycle_status = "MATURED" if days_left <= 0 else "APPROVED_ACTIVE"
            fdr.authority_remarks = f"[RELEASE PETITION REJECTED] {remarks}"
            action_code = "FDR_RELEASE_REJECTED"
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decision must be APPROVE_RELEASE or REJECT_RELEASE")

        db.commit()
        db.refresh(release_req)
        db.refresh(fdr)

        AuditService.log_event(
            db=db,
            action=action_code,
            entity_type="RELEASE_REQUEST",
            entity_id=str(release_req.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            details=f"Authority decision '{decision}' on Release #{release_req.id} for FDR {fdr.fdr_number}: {remarks}",
            ip_address=client_ip
        )

        return release_req

