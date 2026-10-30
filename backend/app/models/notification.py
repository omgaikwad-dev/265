from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    recipient_role = Column(String(50), nullable=True, index=True) # e.g. ROLE_INSTITUTION_ADMIN, ROLE_SCRUTINY_OFFICER
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="SET NULL"), nullable=True, index=True)
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), default="LIFECYCLE", index=True) # MATURITY_ALERT, ESCALATION, SCRUTINY, RELEASE, SYSTEM
    severity = Column(String(20), default="INFO", index=True) # INFO, WARNING, HIGH, CRITICAL
    escalation_level = Column(Integer, default=0) # 0 = Standard, 1 = Tier 1, 2 = Tier 2, 3 = Tier 3
    
    channel = Column(String(30), default="IN_APP") # IN_APP, EMAIL_SIMULATED, SMS_SIMULATED
    delivery_status = Column(String(20), default="DELIVERED") # PENDING, DELIVERED, FAILED
    
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)
    action_link = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])
    institution = relationship("Institution", foreign_keys=[institution_id])
    fdr = relationship("FDRRecord", foreign_keys=[fdr_id])


class EscalationLog(Base):
    __tablename__ = "escalation_logs"

    id = Column(Integer, primary_key=True, index=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    escalation_level = Column(Integer, nullable=False) # 1 = Tier 1, 2 = Tier 2, 3 = Tier 3
    reason = Column(String(255), nullable=False)
    triggered_by = Column(String(50), default="SYSTEM_SCHEDULER")
    recipients_notified = Column(Text, nullable=False) # JSON string of recipients notified
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    fdr = relationship("FDRRecord", foreign_keys=[fdr_id])
    institution = relationship("Institution", foreign_keys=[institution_id])
