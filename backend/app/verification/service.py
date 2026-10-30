from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.fdr import FDRRecord
from app.models.user import User
from app.models.verification import VerificationRule, VerificationReport, Discrepancy
from app.verification.engine import VerificationEngine
from app.audit.service import AuditService

class VerificationService:
    """
    Service layer handling verification execution, discrepancy lifecycle,
    scrutiny observations, and administrative rule configuration.
    """

    @staticmethod
    def run_verification(
        db: Session,
        fdr_id: int,
        current_user: User,
        client_ip: Optional[str] = None
    ) -> VerificationReport:
        """
        Executes all 12 verification rules on the FDR record, generates a report,
        records discrepancies, updates FDR verification status, and writes audit log.
        """
        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FDR record not found")

        user_role = current_user.role.name if current_user.role else None

        # Tenant isolation check
        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != fdr.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot verify FDR belonging to another institution"
            )

        # Execute Engine
        overall_status, rule_results, new_discrepancies = VerificationEngine.evaluate_all_rules(db, fdr)

        passed_count = sum(1 for r in rule_results if r["status"] == "PASSED")
        warning_count = sum(1 for r in rule_results if r["status"] == "WARNING")
        failed_count = sum(1 for r in rule_results if r["status"] == "FAILED")

        # Create VerificationReport
        report = VerificationReport(
            fdr_id=fdr.id,
            overall_status=overall_status,
            total_rules_evaluated=len(rule_results),
            passed_count=passed_count,
            warning_count=warning_count,
            failed_count=failed_count,
            rule_results=rule_results,
            evaluated_by_id=current_user.id
        )
        db.add(report)
        db.flush()

        # Create Discrepancy records
        for d in new_discrepancies:
            disc_record = Discrepancy(
                fdr_id=fdr.id,
                report_id=report.id,
                rule_code=d["rule_code"],
                severity=d["severity"],
                title=d["title"],
                description=d["description"],
                expected_value=d["expected_value"],
                actual_value=d["actual_value"],
                status="OPEN",
                raised_by_role="SYSTEM_VERIFICATION_ENGINE",
                raised_by_user_id=current_user.id
            )
            db.add(disc_record)

        # Update FDR verification status
        if overall_status == "PASSED":
            fdr.verification_status = "VERIFIED"
        elif overall_status == "PASSED_WITH_WARNINGS":
            fdr.verification_status = "VERIFIED_WITH_WARNINGS"
        else:
            fdr.verification_status = "DISCREPANCY_FLAGGED"

        db.commit()
        db.refresh(report)
        db.refresh(fdr)

        # Audit event
        AuditService.log_event(
            db=db,
            action="FDR_VERIFICATION_EVALUATED",
            entity_type="VERIFICATION_REPORT",
            entity_id=str(report.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            details=f"Verification evaluated for FDR {fdr.fdr_number}: Status {overall_status} (Passed: {passed_count}, Warnings: {warning_count}, Failed: {failed_count})",
            ip_address=client_ip
        )

        return report

    @staticmethod
    def get_latest_report(db: Session, fdr_id: int, current_user: User) -> Optional[VerificationReport]:
        """Fetches the latest verification report for an FDR record with tenant enforcement."""
        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FDR record not found")

        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != fdr.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return db.query(VerificationReport).filter(
            VerificationReport.fdr_id == fdr_id
        ).order_by(VerificationReport.created_at.desc()).first()

    @staticmethod
    def get_discrepancies(
        db: Session,
        fdr_id: int,
        current_user: User,
        status_filter: Optional[str] = None
    ) -> List[Discrepancy]:
        """Retrieves discrepancies for an FDR record."""
        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FDR record not found")

        user_role = current_user.role.name if current_user.role else None
        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != fdr.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        query = db.query(Discrepancy).filter(Discrepancy.fdr_id == fdr_id)
        if status_filter:
            query = query.filter(Discrepancy.status == status_filter.upper())
        return query.order_by(Discrepancy.created_at.desc()).all()

    @staticmethod
    def raise_manual_discrepancy(
        db: Session,
        fdr_id: int,
        data: Dict[str, Any],
        current_user: User,
        client_ip: Optional[str] = None
    ) -> Discrepancy:
        """Allows AICTE Scrutiny Officer to raise custom scrutiny observations."""
        user_role = current_user.role.name if current_user.role else None
        if user_role not in ["ROLE_SCRUTINY_OFFICER", "ROLE_SYSTEM_ADMIN", "ROLE_APPROVING_AUTHORITY"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only AICTE Scrutiny Officers or Administrators can raise scrutiny discrepancies"
            )

        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FDR record not found")

        disc = Discrepancy(
            fdr_id=fdr.id,
            report_id=None,
            rule_code=data.get("rule_code", "SCRUTINY_OFFICER_OBSERVATION"),
            severity=data.get("severity", "HIGH"),
            title=data.get("title", "Scrutiny Officer Observation"),
            description=data.get("description", ""),
            expected_value=data.get("expected_value"),
            actual_value=data.get("actual_value"),
            status="OPEN",
            raised_by_role=user_role,
            raised_by_user_id=current_user.id
        )
        db.add(disc)

        # Flag FDR status
        fdr.verification_status = "DISCREPANCY_FLAGGED"
        db.commit()
        db.refresh(disc)

        AuditService.log_event(
            db=db,
            action="MANUAL_DISCREPANCY_RAISED",
            entity_type="DISCREPANCY",
            entity_id=str(disc.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            details=f"Scrutiny observation raised for FDR {fdr.fdr_number}: {disc.title}",
            ip_address=client_ip
        )

        return disc

    @staticmethod
    def respond_to_discrepancy(
        db: Session,
        discrepancy_id: int,
        response_text: str,
        current_user: User,
        client_ip: Optional[str] = None
    ) -> Discrepancy:
        """Allows Institution Admin to submit an explanation or response to an open discrepancy."""
        disc = db.query(Discrepancy).filter(Discrepancy.id == discrepancy_id).first()
        if not disc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discrepancy not found")

        fdr = db.query(FDRRecord).filter(FDRRecord.id == disc.fdr_id).first()
        user_role = current_user.role.name if current_user.role else None

        if user_role == "ROLE_INSTITUTION_ADMIN" and current_user.institution_id != fdr.institution_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        disc.institution_response = response_text
        disc.responded_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(disc)

        AuditService.log_event(
            db=db,
            action="DISCREPANCY_RESPONSE_SUBMITTED",
            entity_type="DISCREPANCY",
            entity_id=str(disc.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            details=f"Institution responded to discrepancy #{disc.id} on FDR {fdr.fdr_number}",
            ip_address=client_ip
        )

        return disc

    @staticmethod
    def resolve_discrepancy(
        db: Session,
        discrepancy_id: int,
        resolution_note: str,
        new_status: str,  # RESOLVED or WAIVED
        current_user: User,
        client_ip: Optional[str] = None
    ) -> Discrepancy:
        """Allows AICTE Scrutiny Officer to mark a discrepancy as RESOLVED or WAIVED."""
        user_role = current_user.role.name if current_user.role else None
        if user_role not in ["ROLE_SCRUTINY_OFFICER", "ROLE_SYSTEM_ADMIN", "ROLE_APPROVING_AUTHORITY"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only AICTE Scrutiny Officers can resolve discrepancies"
            )

        disc = db.query(Discrepancy).filter(Discrepancy.id == discrepancy_id).first()
        if not disc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discrepancy not found")

        if new_status.upper() not in ["RESOLVED", "WAIVED"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status must be RESOLVED or WAIVED")

        disc.status = new_status.upper()
        disc.officer_resolution_note = resolution_note
        disc.resolved_by_user_id = current_user.id
        disc.resolved_at = datetime.now(timezone.utc)

        # Check if all discrepancies for this FDR are now resolved/waived
        remaining_open = db.query(Discrepancy).filter(
            Discrepancy.fdr_id == disc.fdr_id,
            Discrepancy.status == "OPEN"
        ).count()

        fdr = db.query(FDRRecord).filter(FDRRecord.id == disc.fdr_id).first()
        if remaining_open == 0 and fdr:
            fdr.verification_status = "VERIFIED"

        db.commit()
        db.refresh(disc)

        AuditService.log_event(
            db=db,
            action="DISCREPANCY_RESOLVED",
            entity_type="DISCREPANCY",
            entity_id=str(disc.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            details=f"Discrepancy #{disc.id} marked {new_status} by {current_user.username}: {resolution_note}",
            ip_address=client_ip
        )

        return disc

    @staticmethod
    def record_scrutiny_recommendation(
        db: Session,
        fdr_id: int,
        recommendation: str,  # RECOMMEND_APPROVAL, RECOMMEND_REJECTION, NEED_MORE_DOCUMENTS
        remarks: str,
        current_user: User,
        client_ip: Optional[str] = None
    ) -> FDRRecord:
        """Records officer scrutiny finding and recommendation for approving authority."""
        user_role = current_user.role.name if current_user.role else None
        if user_role not in ["ROLE_SCRUTINY_OFFICER", "ROLE_SYSTEM_ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only AICTE Scrutiny Officers can submit scrutiny recommendations"
            )

        fdr = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
        if not fdr:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FDR record not found")

        valid_recommendations = ["RECOMMEND_APPROVAL", "RECOMMEND_REJECTION", "NEED_MORE_DOCUMENTS"]
        if recommendation not in valid_recommendations:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid recommendation. Choose from: {valid_recommendations}")

        fdr.scrutiny_remarks = f"[{recommendation}] {remarks} (By {current_user.full_name} on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})"
        
        if recommendation == "NEED_MORE_DOCUMENTS":
            fdr.lifecycle_status = "DRAFT"  # Returned to institution to attach more documents
        # For RECOMMEND_APPROVAL or RECOMMEND_REJECTION, it remains UNDER_SCRUTINY until Approving Authority signs off in Phase 7

        db.commit()
        db.refresh(fdr)

        AuditService.log_event(
            db=db,
            action="SCRUTINY_RECOMMENDATION_RECORDED",
            entity_type="FDR",
            entity_id=str(fdr.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            details=f"Scrutiny decision recommended: {recommendation} for FDR {fdr.fdr_number}",
            ip_address=client_ip
        )

        return fdr

    # -------------------------------------------------------------------------
    # RULE CONFIGURATION (ADMINISTRATIVE)
    # -------------------------------------------------------------------------
    @staticmethod
    def get_all_rules(db: Session) -> List[VerificationRule]:
        """Returns all configurable verification rules."""
        return db.query(VerificationRule).order_by(VerificationRule.id.asc()).all()

    @staticmethod
    def update_rule(
        db: Session,
        rule_id: int,
        update_data: Dict[str, Any],
        current_user: User,
        client_ip: Optional[str] = None
    ) -> VerificationRule:
        """Allows System Administrator to configure rule parameters and toggle enablement."""
        user_role = current_user.role.name if current_user.role else None
        if user_role != "ROLE_SYSTEM_ADMIN":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only System Administrators can configure verification rules")

        rule = db.query(VerificationRule).filter(VerificationRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

        if "is_enabled" in update_data:
            rule.is_enabled = bool(update_data["is_enabled"])
        if "severity" in update_data and update_data["severity"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            rule.severity = update_data["severity"]
        if "parameters" in update_data and isinstance(update_data["parameters"], dict):
            rule.parameters = {**rule.parameters, **update_data["parameters"]}

        db.commit()
        db.refresh(rule)

        AuditService.log_event(
            db=db,
            action="VERIFICATION_RULE_CONFIGURED",
            entity_type="VERIFICATION_RULE",
            entity_id=str(rule.id),
            user_id=current_user.id,
            username=current_user.username,
            role=user_role,
            details=f"Rule {rule.rule_code} configured: Enabled={rule.is_enabled}, Severity={rule.severity}",
            ip_address=client_ip
        )

        return rule
