import json
import logging
from datetime import date, datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException, status

from app.models.notification import Notification, EscalationLog
from app.models.fdr import FDRRecord
from app.models.user import User, Role
from app.models.institution import Institution
from app.audit.service import AuditService

logger = logging.getLogger("fdrsetu.notifications")

class NotificationService:
    """
    Core engine managing in-app notifications, multi-channel dispatch simulation (Email/SMS),
    milestone maturity alerts, and multi-tier automated escalations.
    """

    @staticmethod
    def create_notification(
        db: Session,
        title: str,
        message: str,
        category: str = "LIFECYCLE",
        severity: str = "INFO",
        escalation_level: int = 0,
        recipient_user_id: Optional[int] = None,
        recipient_role: Optional[str] = None,
        institution_id: Optional[int] = None,
        fdr_id: Optional[int] = None,
        channel: str = "IN_APP",
        action_link: Optional[str] = None
    ) -> Notification:
        """
        Creates and persists a notification, simulating multi-channel dispatch when required.
        """
        notification = Notification(
            title=title,
            message=message,
            category=category,
            severity=severity,
            escalation_level=escalation_level,
            recipient_user_id=recipient_user_id,
            recipient_role=recipient_role,
            institution_id=institution_id,
            fdr_id=fdr_id,
            channel=channel,
            delivery_status="DELIVERED",
            action_link=action_link,
            is_read=False
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        # Log simulated channel dispatches
        if channel in ("EMAIL_SIMULATED", "SMS_SIMULATED") or severity in ("HIGH", "CRITICAL"):
            logger.info(
                f"[DISPATCH SIMULATOR] Channel={channel} | Severity={severity} | "
                f"RecipientRole={recipient_role} | InstID={institution_id} | Title={title}"
            )

        return notification

    @staticmethod
    def get_user_notifications(
        db: Session,
        current_user: User,
        category: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Retrieves notifications accessible to the current user adhering strictly to RBAC and tenant boundaries.
        """
        user_role = current_user.role.name if current_user.role else ""

        query = db.query(Notification)

        # Tenant & Role Isolation
        if user_role == "ROLE_INSTITUTION_ADMIN":
            if not current_user.institution_id:
                return {"unread_count": 0, "total_count": 0, "items": []}
            query = query.filter(
                or_(
                    Notification.recipient_user_id == current_user.id,
                    and_(
                        Notification.institution_id == current_user.institution_id,
                        or_(
                            Notification.recipient_role == "ROLE_INSTITUTION_ADMIN",
                            Notification.recipient_role.is_(None)
                        )
                    )
                )
            )
        elif user_role == "ROLE_SCRUTINY_OFFICER":
            query = query.filter(
                or_(
                    Notification.recipient_user_id == current_user.id,
                    Notification.recipient_role == "ROLE_SCRUTINY_OFFICER"
                )
            )
        elif user_role == "ROLE_APPROVING_AUTHORITY":
            query = query.filter(
                or_(
                    Notification.recipient_user_id == current_user.id,
                    Notification.recipient_role == "ROLE_APPROVING_AUTHORITY"
                )
            )
        elif user_role in ("ROLE_SYSTEM_ADMIN", "ROLE_AUDITOR"):
            # System Admin and Auditor can inspect system-wide notifications
            pass
        else:
            query = query.filter(Notification.recipient_user_id == current_user.id)

        # Filters
        if category:
            query = query.filter(Notification.category == category)
        
        # Calculate unread count before applying unread_only filter
        unread_count = query.filter(Notification.is_read == False).count()
        total_count = query.count()

        if unread_only:
            query = query.filter(Notification.is_read == False)

        items = query.order_by(desc(Notification.created_at)).offset(offset).limit(limit).all()

        return {
            "unread_count": unread_count,
            "total_count": total_count,
            "items": items
        }

    @staticmethod
    def mark_notification_as_read(
        db: Session,
        notification_id: int,
        current_user: User
    ) -> Notification:
        """
        Marks an individual notification as read with strict authorization checks.
        """
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification #{notification_id} not found"
            )

        user_role = current_user.role.name if current_user.role else ""

        # Authorization check
        if user_role == "ROLE_INSTITUTION_ADMIN":
            if notification.institution_id and notification.institution_id != current_user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to cross-institutional notification"
                )
        elif user_role not in ("ROLE_SYSTEM_ADMIN", "ROLE_AUDITOR"):
            if notification.recipient_user_id and notification.recipient_user_id != current_user.id:
                if notification.recipient_role and notification.recipient_role != user_role:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to this notification"
                    )

        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def mark_all_as_read(
        db: Session,
        current_user: User
    ) -> int:
        """
        Marks all eligible notifications for the user's role/tenant as read.
        """
        user_role = current_user.role.name if current_user.role else ""
        query = db.query(Notification).filter(Notification.is_read == False)

        if user_role == "ROLE_INSTITUTION_ADMIN":
            if not current_user.institution_id:
                return 0
            query = query.filter(
                or_(
                    Notification.recipient_user_id == current_user.id,
                    and_(
                        Notification.institution_id == current_user.institution_id,
                        or_(
                            Notification.recipient_role == "ROLE_INSTITUTION_ADMIN",
                            Notification.recipient_role.is_(None)
                        )
                    )
                )
            )
        elif user_role == "ROLE_SCRUTINY_OFFICER":
            query = query.filter(
                or_(
                    Notification.recipient_user_id == current_user.id,
                    Notification.recipient_role == "ROLE_SCRUTINY_OFFICER"
                )
            )
        elif user_role == "ROLE_APPROVING_AUTHORITY":
            query = query.filter(
                or_(
                    Notification.recipient_user_id == current_user.id,
                    Notification.recipient_role == "ROLE_APPROVING_AUTHORITY"
                )
            )
        elif user_role in ("ROLE_SYSTEM_ADMIN", "ROLE_AUDITOR"):
            pass
        else:
            query = query.filter(Notification.recipient_user_id == current_user.id)

        unread_items = query.all()
        now = datetime.now(timezone.utc)
        count = 0
        for item in unread_items:
            item.is_read = True
            item.read_at = now
            count += 1

        db.commit()
        return count

    @staticmethod
    def run_escalation_engine(
        db: Session,
        trigger_source: str = "MANUAL_OR_CRON",
        triggered_by_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Executes maturity alerts (90, 60, 30, 15, 7, 0 days) and 3-Tier Non-Compliance Escalations:
        - Tier 1: 7 days overdue -> Alert to Institution Nodal Officer & Head
        - Tier 2: 15 days overdue -> Alert to AICTE Scrutiny Officer
        - Tier 3: 30 days overdue -> Urgent Alert to AICTE Approving Authority / Regional Director
        """
        today = date.today()
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)

        # Scan active and overdue FDRs
        active_fdrs = db.query(FDRRecord).filter(
            FDRRecord.lifecycle_status.in_(["APPROVED_ACTIVE", "RENEWAL_DUE", "MATURED"])
        ).all()

        scanned_count = len(active_fdrs)
        escalations_triggered = 0
        notifications_dispatched = 0
        details = []

        for fdr in active_fdrs:
            if not fdr.maturity_date:
                continue

            days_left = (fdr.maturity_date - today).days

            # ----------------------------------------------------
            # 1. MILESTONE MATURITY ALERTS (90, 60, 30, 15, 7, 0)
            # ----------------------------------------------------
            if days_left in (90, 60, 30, 15, 7, 0):
                milestone_title = f"Maturity Alert: FDR #{fdr.fdr_number} matures in {days_left} days" if days_left > 0 else f"Maturity Alert: FDR #{fdr.fdr_number} MATURES TODAY"
                
                # Check deduplication: avoid duplicate alert for same milestone within 24h
                existing_alert = db.query(Notification).filter(
                    Notification.fdr_id == fdr.id,
                    Notification.category == "MATURITY_ALERT",
                    Notification.title == milestone_title,
                    Notification.created_at >= one_day_ago
                ).first()

                if not existing_alert:
                    sev = "INFO" if days_left in (90, 60) else ("WARNING" if days_left in (30, 15) else "HIGH")
                    NotificationService.create_notification(
                        db=db,
                        title=milestone_title,
                        message=(
                            f"Fixed Deposit Receipt #{fdr.fdr_number} (Amount: ₹{fdr.deposit_amount:,.2f}) at "
                            f"{fdr.bank_name} is approaching its maturity date ({fdr.maturity_date}). "
                            f"Please initiate renewal or statutory refund proceedings promptly."
                        ),
                        category="MATURITY_ALERT",
                        severity=sev,
                        recipient_role="ROLE_INSTITUTION_ADMIN",
                        institution_id=fdr.institution_id,
                        fdr_id=fdr.id,
                        channel="EMAIL_SIMULATED",
                        action_link=f"/fdrs/{fdr.id}"
                    )
                    notifications_dispatched += 1
                    details.append({
                        "fdr_id": fdr.id,
                        "type": "MILESTONE_ALERT",
                        "days_left": days_left,
                        "severity": sev
                    })

            # ----------------------------------------------------
            # 2. MULTI-TIER ESCALATION ENGINE (POST-MATURITY / DUE)
            # ----------------------------------------------------
            # Tier 3: 30+ days overdue
            if days_left <= -30:
                recent_log = db.query(EscalationLog).filter(
                    EscalationLog.fdr_id == fdr.id,
                    EscalationLog.escalation_level == 3,
                    EscalationLog.created_at >= (now - timedelta(days=30))
                ).first()

                if not recent_log:
                    recipients = ["ROLE_APPROVING_AUTHORITY", "ROLE_SCRUTINY_OFFICER", "ROLE_INSTITUTION_ADMIN"]
                    log = EscalationLog(
                        fdr_id=fdr.id,
                        institution_id=fdr.institution_id,
                        escalation_level=3,
                        reason=f"Security deposit overdue by {abs(days_left)} days without compliance action",
                        triggered_by=trigger_source,
                        recipients_notified=json.dumps(recipients)
                    )
                    db.add(log)
                    db.commit()

                    # Notify Approving Authority (Regional Director)
                    NotificationService.create_notification(
                        db=db,
                        title=f"[ESCALATION TIER 3 - REGIONAL URGENT] Overdue Security Deposit #{fdr.fdr_number}",
                        message=(
                            f"CRITICAL NOTICE: FDR #{fdr.fdr_number} for Institution #{fdr.institution_id} is "
                            f"{abs(days_left)} days past maturity ({fdr.maturity_date}). Institutional non-compliance "
                            f"has breached 30-day statutory grace period. Formal regulatory review required."
                        ),
                        category="ESCALATION",
                        severity="CRITICAL",
                        escalation_level=3,
                        recipient_role="ROLE_APPROVING_AUTHORITY",
                        institution_id=fdr.institution_id,
                        fdr_id=fdr.id,
                        channel="EMAIL_SIMULATED",
                        action_link=f"/fdrs/{fdr.id}"
                    )
                    # Notify Scrutiny Officer
                    NotificationService.create_notification(
                        db=db,
                        title=f"[ESCALATION TIER 3] Non-Compliance Escalated - FDR #{fdr.fdr_number}",
                        message=f"FDR #{fdr.fdr_number} is {abs(days_left)} days overdue. Escalated to Approving Authority.",
                        category="ESCALATION",
                        severity="CRITICAL",
                        escalation_level=3,
                        recipient_role="ROLE_SCRUTINY_OFFICER",
                        institution_id=fdr.institution_id,
                        fdr_id=fdr.id,
                        channel="IN_APP",
                        action_link=f"/fdrs/{fdr.id}"
                    )
                    # Notify Institution Head
                    NotificationService.create_notification(
                        db=db,
                        title=f"[LEGAL WARNING TIER 3] Immediate Action Required: Overdue Security Deposit #{fdr.fdr_number}",
                        message=(
                            f"FINAL NOTICE: FDR #{fdr.fdr_number} is {abs(days_left)} days past maturity. "
                            f"AICTE Regional Office has been alerted. Submit renewal or refund request immediately to avoid regulatory sanctions."
                        ),
                        category="ESCALATION",
                        severity="CRITICAL",
                        escalation_level=3,
                        recipient_role="ROLE_INSTITUTION_ADMIN",
                        institution_id=fdr.institution_id,
                        fdr_id=fdr.id,
                        channel="EMAIL_SIMULATED",
                        action_link=f"/fdrs/{fdr.id}"
                    )

                    escalations_triggered += 1
                    notifications_dispatched += 3
                    details.append({"fdr_id": fdr.id, "type": "TIER_3_ESCALATION", "days_overdue": abs(days_left)})

            # Tier 2: 15 to 29 days overdue
            elif days_left <= -15:
                recent_log = db.query(EscalationLog).filter(
                    EscalationLog.fdr_id == fdr.id,
                    EscalationLog.escalation_level == 2,
                    EscalationLog.created_at >= (now - timedelta(days=14))
                ).first()

                if not recent_log:
                    recipients = ["ROLE_SCRUTINY_OFFICER", "ROLE_INSTITUTION_ADMIN"]
                    log = EscalationLog(
                        fdr_id=fdr.id,
                        institution_id=fdr.institution_id,
                        escalation_level=2,
                        reason=f"Security deposit overdue by {abs(days_left)} days without renewal submission",
                        triggered_by=trigger_source,
                        recipients_notified=json.dumps(recipients)
                    )
                    db.add(log)
                    db.commit()

                    # Notify Scrutiny Officer
                    NotificationService.create_notification(
                        db=db,
                        title=f"[ESCALATION TIER 2] Non-Compliance Flag: Overdue FDR #{fdr.fdr_number}",
                        message=(
                            f"FDR #{fdr.fdr_number} (Amount: ₹{fdr.deposit_amount:,.2f}) for Institution #{fdr.institution_id} "
                            f"is {abs(days_left)} days past maturity without renewal or release request."
                        ),
                        category="ESCALATION",
                        severity="HIGH",
                        escalation_level=2,
                        recipient_role="ROLE_SCRUTINY_OFFICER",
                        institution_id=fdr.institution_id,
                        fdr_id=fdr.id,
                        channel="IN_APP",
                        action_link=f"/fdrs/{fdr.id}"
                    )
                    # Notify Institution Admin
                    NotificationService.create_notification(
                        db=db,
                        title=f"[ESCALATION TIER 2] Scrutiny Flag Raised: FDR #{fdr.fdr_number} Overdue",
                        message=(
                            f"Your Fixed Deposit #{fdr.fdr_number} is {abs(days_left)} days past maturity. "
                            f"AICTE Scrutiny Officers have been notified of this non-compliance."
                        ),
                        category="ESCALATION",
                        severity="HIGH",
                        escalation_level=2,
                        recipient_role="ROLE_INSTITUTION_ADMIN",
                        institution_id=fdr.institution_id,
                        fdr_id=fdr.id,
                        channel="EMAIL_SIMULATED",
                        action_link=f"/fdrs/{fdr.id}"
                    )

                    escalations_triggered += 1
                    notifications_dispatched += 2
                    details.append({"fdr_id": fdr.id, "type": "TIER_2_ESCALATION", "days_overdue": abs(days_left)})

            # Tier 1: 7 to 14 days overdue
            elif days_left <= -7:
                recent_log = db.query(EscalationLog).filter(
                    EscalationLog.fdr_id == fdr.id,
                    EscalationLog.escalation_level == 1,
                    EscalationLog.created_at >= (now - timedelta(days=7))
                ).first()

                if not recent_log:
                    recipients = ["ROLE_INSTITUTION_ADMIN"]
                    log = EscalationLog(
                        fdr_id=fdr.id,
                        institution_id=fdr.institution_id,
                        escalation_level=1,
                        reason=f"Security deposit overdue by {abs(days_left)} days",
                        triggered_by=trigger_source,
                        recipients_notified=json.dumps(recipients)
                    )
                    db.add(log)
                    db.commit()

                    # Notify Institution Admin / Nodal Officer
                    NotificationService.create_notification(
                        db=db,
                        title=f"[ESCALATION TIER 1] Security Deposit Overdue: FDR #{fdr.fdr_number}",
                        message=(
                            f"FDR #{fdr.fdr_number} is {abs(days_left)} days past maturity date ({fdr.maturity_date}). "
                            f"Please upload renewal instrument or initiate formal release petition immediately."
                        ),
                        category="ESCALATION",
                        severity="WARNING",
                        escalation_level=1,
                        recipient_role="ROLE_INSTITUTION_ADMIN",
                        institution_id=fdr.institution_id,
                        fdr_id=fdr.id,
                        channel="EMAIL_SIMULATED",
                        action_link=f"/fdrs/{fdr.id}"
                    )

                    escalations_triggered += 1
                    notifications_dispatched += 1
                    details.append({"fdr_id": fdr.id, "type": "TIER_1_ESCALATION", "days_overdue": abs(days_left)})

        # Audit log summary if triggered manually or escalations occurred
        if escalations_triggered > 0 or triggered_by_user:
            AuditService.log_event(
                db=db,
                action="ESCALATION_ENGINE_RUN",
                entity_type="Notification",
                entity_id="ESCALATION_SCAN",
                user_id=triggered_by_user.id if triggered_by_user else None,
                username=triggered_by_user.username if triggered_by_user else "SYSTEM_AUTOMATION",
                role=triggered_by_user.role.name if triggered_by_user and triggered_by_user.role else "SYSTEM",
                details=json.dumps({
                    "trigger_source": trigger_source,
                    "scanned_count": scanned_count,
                    "escalations_triggered": escalations_triggered,
                    "notifications_dispatched": notifications_dispatched
                }),
                ip_address="127.0.0.1"
            )

        return {
            "scanned_fdrs": scanned_count,
            "escalations_triggered": escalations_triggered,
            "notifications_dispatched": notifications_dispatched,
            "details": details
        }

    @staticmethod
    def get_escalation_history(
        db: Session,
        current_user: User,
        fdr_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[EscalationLog]:
        """
        Retrieves escalation history with role and tenant isolation.
        """
        user_role = current_user.role.name if current_user.role else ""
        query = db.query(EscalationLog)

        if user_role == "ROLE_INSTITUTION_ADMIN":
            if not current_user.institution_id:
                return []
            query = query.filter(EscalationLog.institution_id == current_user.institution_id)

        if fdr_id:
            query = query.filter(EscalationLog.fdr_id == fdr_id)

        return query.order_by(desc(EscalationLog.created_at)).offset(offset).limit(limit).all()
