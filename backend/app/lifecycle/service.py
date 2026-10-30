from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.fdr import FDRRecord, FDRDocument
from app.models.user import User
from app.audit.service import AuditService

class LifecycleService:
    """
    Manages FDR lifecycle state transitions, maturity timeline calculation,
    automated status progression (RENEWAL_DUE, MATURED), and renewal/replacement chains.
    """

    @staticmethod
    def calculate_maturity_status(maturity_date: Optional[date]) -> Dict[str, Any]:
        """
        Dynamically calculates days to maturity and assigns the milestone bucket.
        """
        if not maturity_date:
            return {
                "days_to_maturity": None,
                "milestone": "UNKNOWN",
                "urgency": "NORMAL",
                "is_matured": False,
                "is_renewal_due": False
            }

        today = date.today()
        days_left = (maturity_date - today).days

        if days_left < 0:
            milestone = "OVERDUE_MATURED"
            urgency = "CRITICAL"
        elif days_left == 0:
            milestone = "MATURES_TODAY"
            urgency = "CRITICAL"
        elif days_left <= 7:
            milestone = "WITHIN_7_DAYS"
            urgency = "HIGH"
        elif days_left <= 15:
            milestone = "WITHIN_15_DAYS"
            urgency = "HIGH"
        elif days_left <= 30:
            milestone = "WITHIN_30_DAYS"
            urgency = "MEDIUM"
        elif days_left <= 60:
            milestone = "WITHIN_60_DAYS"
            urgency = "MEDIUM"
        elif days_left <= 90:
            milestone = "WITHIN_90_DAYS"
            urgency = "LOW"
        else:
            milestone = "HEALTHY_ACTIVE"
            urgency = "NORMAL"

        return {
            "days_to_maturity": days_left,
            "milestone": milestone,
            "urgency": urgency,
            "is_matured": days_left <= 0,
            "is_renewal_due": 0 < days_left <= 90
        }

    @staticmethod
    def scan_and_update_maturities(
        db: Session,
        trigger_source: str = "MANUAL_OR_CRON",
        triggered_by_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Scans all FDR records across the database and performs automated state transitions:
        - If days <= 0 and status in [APPROVED_ACTIVE, RENEWAL_DUE] -> MATURED
        - If 0 < days <= 90 and status == APPROVED_ACTIVE -> RENEWAL_DUE
        """
        today = date.today()

        # Candidates for maturity transitions
        candidates = db.query(FDRRecord).filter(
            FDRRecord.lifecycle_status.in_(["APPROVED_ACTIVE", "RENEWAL_DUE", "RENEWAL_SUBMITTED"])
        ).all()

        total_scanned = len(candidates)
        matured_transitions = []
        renewal_due_transitions = []

        for fdr in candidates:
            if not fdr.maturity_date:
                continue

            days_left = (fdr.maturity_date - today).days

            # Case 1: Matured
            if days_left <= 0 and fdr.lifecycle_status != "MATURED":
                prev_status = fdr.lifecycle_status
                fdr.lifecycle_status = "MATURED"
                matured_transitions.append({
                    "fdr_id": fdr.id,
                    "fdr_number": fdr.fdr_number,
                    "previous_status": prev_status,
                    "maturity_date": str(fdr.maturity_date),
                    "days_overdue": abs(days_left)
                })

                AuditService.log_event(
                    db=db,
                    action="FDR_STATUS_TRANSITION_MATURED",
                    entity_type="FDR",
                    entity_id=str(fdr.id),
                    user_id=triggered_by_user.id if triggered_by_user else None,
                    username=triggered_by_user.username if triggered_by_user else "SYSTEM_SCHEDULER",
                    role="SYSTEM_AUTOMATION",
                    details=f"Automated maturity scan: FDR {fdr.fdr_number} transitioned from {prev_status} to MATURED ({days_left} days left).",
                    ip_address="127.0.0.1"
                )

            # Case 2: Renewal Due (within 90 days)
            elif 0 < days_left <= 90 and fdr.lifecycle_status == "APPROVED_ACTIVE":
                fdr.lifecycle_status = "RENEWAL_DUE"
                renewal_due_transitions.append({
                    "fdr_id": fdr.id,
                    "fdr_number": fdr.fdr_number,
                    "days_left": days_left,
                    "maturity_date": str(fdr.maturity_date)
                })

                AuditService.log_event(
                    db=db,
                    action="FDR_STATUS_TRANSITION_RENEWAL_DUE",
                    entity_type="FDR",
                    entity_id=str(fdr.id),
                    user_id=triggered_by_user.id if triggered_by_user else None,
                    username=triggered_by_user.username if triggered_by_user else "SYSTEM_SCHEDULER",
                    role="SYSTEM_AUTOMATION",
                    details=f"Automated maturity scan: FDR {fdr.fdr_number} flagged as RENEWAL_DUE ({days_left} days left until {fdr.maturity_date}).",
                    ip_address="127.0.0.1"
                )

        db.commit()

        return {
            "status": "success",
            "trigger_source": trigger_source,
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_scanned": total_scanned,
            "matured_count": len(matured_transitions),
            "renewal_due_count": len(renewal_due_transitions),
            "matured_instruments": matured_transitions,
            "renewal_due_instruments": renewal_due_transitions
        }

    @staticmethod
    def get_maturity_timeline(
        db: Session,
        current_user: User,
        institution_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Compiles dynamic calendar metrics and upcoming maturity schedule.
        """
        user_role = current_user.role.name if current_user.role else None

        query = db.query(FDRRecord)
        if user_role == "ROLE_INSTITUTION_ADMIN":
            query = query.filter(FDRRecord.institution_id == current_user.institution_id)
        elif institution_id:
            query = query.filter(FDRRecord.institution_id == institution_id)

        all_fdrs = query.all()

        buckets = {
            "OVERDUE_MATURED": [],
            "WITHIN_7_DAYS": [],
            "WITHIN_30_DAYS": [],
            "WITHIN_60_DAYS": [],
            "WITHIN_90_DAYS": [],
            "HEALTHY_ACTIVE": []
        }

        total_statutory_value = Decimal("0.00")

        for fdr in all_fdrs:
            calc = LifecycleService.calculate_maturity_status(fdr.maturity_date)
            ms = calc["milestone"]
            
            fdr_summary = {
                "id": fdr.id,
                "fdr_number": fdr.fdr_number,
                "bank_name": fdr.bank_name,
                "deposit_amount": float(fdr.deposit_amount or 0),
                "issue_date": str(fdr.issue_date),
                "maturity_date": str(fdr.maturity_date),
                "lifecycle_status": fdr.lifecycle_status,
                "days_to_maturity": calc["days_to_maturity"],
                "urgency": calc["urgency"]
            }

            if ms in ["OVERDUE_MATURED", "MATURES_TODAY"]:
                buckets["OVERDUE_MATURED"].append(fdr_summary)
            elif ms in ["WITHIN_7_DAYS", "WITHIN_15_DAYS"]:
                buckets["WITHIN_7_DAYS"].append(fdr_summary)
            elif ms == "WITHIN_30_DAYS":
                buckets["WITHIN_30_DAYS"].append(fdr_summary)
            elif ms == "WITHIN_60_DAYS":
                buckets["WITHIN_60_DAYS"].append(fdr_summary)
            elif ms == "WITHIN_90_DAYS":
                buckets["WITHIN_90_DAYS"].append(fdr_summary)
            else:
                buckets["HEALTHY_ACTIVE"].append(fdr_summary)

            if fdr.lifecycle_status in ["APPROVED_ACTIVE", "RENEWAL_DUE", "UNDER_SCRUTINY"]:
                total_statutory_value += Decimal(str(fdr.deposit_amount or 0))

        return {
            "total_instruments": len(all_fdrs),
            "total_statutory_value": float(total_statutory_value),
            "buckets": buckets,
            "counts": {k: len(v) for k, v in buckets.items()}
        }

    # -------------------------------------------------------------------------
    # RENEWAL & REPLACEMENT CHAINING
    # -------------------------------------------------------------------------
    @staticmethod
    def initiate_renewal(
        db: Session,
        previous_fdr_id: int,
        renewal_payload: Dict[str, Any],
        current_user: User,
        client_ip: Optional[str] = None
    ) -> FDRRecord:
        """
        Initiates an instrument renewal linked to an existing FDR.
        Preserves complete chained lineage and updates the original FDR status to RENEWAL_SUBMITTED.
        """
        prev_fdr = db.query(FDRRecord).filter(FDRRecord.id == previous_fdr_id).first()
        if not prev_fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original FDR not found")

        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != prev_fdr.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # Create the new renewed FDR in DRAFT status
        new_fdr_num = renewal_payload.get("fdr_number", f"{prev_fdr.fdr_number}-RNW").strip()
        
        # Verify duplicate
        dup = db.query(FDRRecord).filter(
            FDRRecord.fdr_number == new_fdr_num,
            FDRRecord.bank_name.ilike(renewal_payload.get("bank_name", prev_fdr.bank_name))
        ).first()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An FDR with number '{new_fdr_num}' already exists in the system."
            )

        renewed_fdr = FDRRecord(
            institution_id=prev_fdr.institution_id,
            fdr_number=new_fdr_num,
            bank_name=renewal_payload.get("bank_name", prev_fdr.bank_name),
            branch_name=renewal_payload.get("branch_name", prev_fdr.branch_name),
            ifsc_code=renewal_payload.get("ifsc_code", prev_fdr.ifsc_code),
            deposit_amount=renewal_payload.get("deposit_amount", prev_fdr.deposit_amount),
            issue_date=renewal_payload.get("issue_date", date.today()),
            maturity_date=renewal_payload.get("maturity_date", prev_fdr.maturity_date),
            interest_rate=renewal_payload.get("interest_rate", prev_fdr.interest_rate),
            beneficiary=renewal_payload.get("beneficiary", prev_fdr.beneficiary),
            joint_holder=renewal_payload.get("joint_holder", prev_fdr.joint_holder),
            instrument_type=renewal_payload.get("instrument_type", prev_fdr.instrument_type),
            is_auto_renewal=renewal_payload.get("is_auto_renewal", prev_fdr.is_auto_renewal),
            previous_fdr_id=prev_fdr.id,
            ocr_status="MANUALLY_ENTERED",
            verification_status="UNVERIFIED",
            lifecycle_status="DRAFT"
        )
        db.add(renewed_fdr)
        
        # Mark previous FDR as RENEWAL_SUBMITTED
        prev_fdr.lifecycle_status = "RENEWAL_SUBMITTED"

        db.commit()
        db.refresh(renewed_fdr)
        db.refresh(prev_fdr)

        AuditService.log_event(
            db=db,
            action="FDR_RENEWAL_INITIATED",
            entity_type="FDR",
            entity_id=str(renewed_fdr.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            details=f"Renewal FDR {renewed_fdr.fdr_number} initiated for previous FDR {prev_fdr.fdr_number} (ID {prev_fdr.id})",
            ip_address=client_ip
        )

        return renewed_fdr

    @staticmethod
    def get_renewal_lineage(
        db: Session,
        fdr_id: int,
        current_user: User
    ) -> List[Dict[str, Any]]:
        """
        Traverses the complete bidirectional lineage chain (ancestors and descendants).
        """
        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FDR not found")

        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != fdr.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        # 1. Trace root
        root = fdr
        while root.previous_fdr_id:
            parent = db.query(FDRRecord).filter(FDRRecord.id == root.previous_fdr_id).first()
            if not parent:
                break
            root = parent

        # 2. Build forward chain from root
        chain = []
        curr = root
        visited = set()

        while curr and curr.id not in visited:
            visited.add(curr.id)
            chain.append({
                "id": curr.id,
                "fdr_number": curr.fdr_number,
                "bank_name": curr.bank_name,
                "deposit_amount": float(curr.deposit_amount or 0),
                "issue_date": str(curr.issue_date),
                "maturity_date": str(curr.maturity_date),
                "lifecycle_status": curr.lifecycle_status,
                "verification_status": curr.verification_status,
                "is_current": curr.id == fdr.id
            })

            # Find next in chain
            next_fdr = db.query(FDRRecord).filter(FDRRecord.previous_fdr_id == curr.id).first()
            curr = next_fdr

        return chain

