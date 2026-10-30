from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.user import User
from app.notifications.service import NotificationService
from app.schemas.notification import (
    NotificationOut,
    NotificationListOut,
    NotificationCreate,
    EscalationLogOut,
    EscalationScanResult
)

router = APIRouter(prefix="/notifications", tags=["Notifications & Escalation Engine"])

@router.get("", response_model=NotificationListOut)
def get_user_notifications(
    category: Optional[str] = Query(None, description="Filter by category: MATURITY_ALERT, ESCALATION, SCRUTINY, RELEASE, SYSTEM"),
    unread_only: bool = Query(False, description="Filter unread notifications only"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves in-app notification feed for the authenticated user, enforcing multi-tenant isolation.
    """
    return NotificationService.get_user_notifications(
        db=db,
        current_user=current_user,
        category=category,
        unread_only=unread_only,
        limit=limit,
        offset=offset
    )

@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks an individual notification as read.
    """
    return NotificationService.mark_notification_as_read(
        db=db,
        notification_id=notification_id,
        current_user=current_user
    )

@router.post("/mark-all-read")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks all notifications for the active user / tenant as read.
    """
    count = NotificationService.mark_all_as_read(db=db, current_user=current_user)
    return {"marked_count": count, "message": f"Marked {count} notifications as read."}

@router.post("/trigger-escalation", response_model=EscalationScanResult)
def trigger_escalation_engine(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ROLE_SYSTEM_ADMIN", "ROLE_APPROVING_AUTHORITY", "ROLE_SCRUTINY_OFFICER"))
):
    """
    Manually triggers the milestone maturity alert and multi-tier escalation engine scan.
    """
    return NotificationService.run_escalation_engine(
        db=db,
        trigger_source=f"MANUAL_TRIGGER_BY_{current_user.email}",
        triggered_by_user=current_user
    )

@router.get("/escalation-logs", response_model=List[EscalationLogOut])
def get_escalation_logs(
    fdr_id: Optional[int] = Query(None, description="Filter escalation logs by FDR ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves multi-tier escalation history with tenant isolation.
    """
    return NotificationService.get_escalation_history(
        db=db,
        current_user=current_user,
        fdr_id=fdr_id,
        limit=limit,
        offset=offset
    )

@router.post("/test-dispatch", response_model=NotificationOut)
def send_test_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ROLE_SYSTEM_ADMIN", "ROLE_SCRUTINY_OFFICER"))
):
    """
    Administrative endpoint to dispatch simulated multi-channel notifications.
    """
    return NotificationService.create_notification(
        db=db,
        title=payload.title,
        message=payload.message,
        category=payload.category,
        severity=payload.severity,
        escalation_level=payload.escalation_level,
        recipient_user_id=payload.recipient_user_id,
        recipient_role=payload.recipient_role,
        institution_id=payload.institution_id,
        fdr_id=payload.fdr_id,
        channel=payload.channel,
        action_link=payload.action_link
    )
