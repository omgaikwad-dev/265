from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class ReleaseRequest(Base):
    __tablename__ = "release_requests"

    id = Column(Integer, primary_key=True, index=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    release_reason = Column(Text, nullable=False)
    refund_bank_name = Column(String(100), nullable=False)
    refund_account_number = Column(String(50), nullable=False)
    refund_ifsc = Column(String(20), nullable=False)
    refund_beneficiary_name = Column(String(150), nullable=False)
    noc_document_id = Column(Integer, ForeignKey("fdr_documents.id", ondelete="SET NULL"), nullable=True)

    status = Column(String(30), default="PENDING", nullable=False, index=True)  # PENDING, APPROVED, REJECTED
    authority_remarks = Column(Text, nullable=True)
    authorization_reference = Column(String(100), nullable=True)
    decided_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    fdr = relationship("FDRRecord", backref="release_requests")
    institution = relationship("Institution", backref="release_requests")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    decided_by = relationship("User", foreign_keys=[decided_by_id])
    noc_document = relationship("FDRDocument", foreign_keys=[noc_document_id])

