from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class NotificationBase(BaseModel):
    title: str
    message: str
    category: str = "LIFECYCLE"
    severity: str = "INFO"
    escalation_level: int = 0
    channel: str = "IN_APP"
    action_link: Optional[str] = None

class NotificationCreate(NotificationBase):
    recipient_user_id: Optional[int] = None
    recipient_role: Optional[str] = None
    institution_id: Optional[int] = None
    fdr_id: Optional[int] = None

class NotificationOut(NotificationBase):
    id: int
    recipient_user_id: Optional[int] = None
    recipient_role: Optional[str] = None
    institution_id: Optional[int] = None
    fdr_id: Optional[int] = None
    delivery_status: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationListOut(BaseModel):
    unread_count: int
    total_count: int
    items: List[NotificationOut]

class EscalationLogOut(BaseModel):
    id: int
    fdr_id: int
    institution_id: int
    escalation_level: int
    reason: str
    triggered_by: str
    recipients_notified: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EscalationScanResult(BaseModel):
    scanned_fdrs: int
    escalations_triggered: int
    notifications_dispatched: int
    details: List[Dict[str, Any]] = []
