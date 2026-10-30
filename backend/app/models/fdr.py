from datetime import datetime, date, timezone
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class FDRRecord(Base):
    __tablename__ = "fdr_records"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    submitted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Core Financial Instrument Identifiers
    fdr_number = Column(String(100), nullable=False, index=True)
    bank_name = Column(String(150), nullable=False, index=True)
    branch_name = Column(String(150), nullable=False)
    ifsc_code = Column(String(20), nullable=False, index=True)
    
    # Financial Terms (Numeric for exact currency precision)
    deposit_amount = Column(Numeric(15, 2), nullable=False)
    issue_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False, index=True)
    interest_rate = Column(Numeric(5, 2), nullable=True)

    # Beneficiary & Legal Ownership
    beneficiary = Column(String(255), default="Member Secretary, AICTE / Regional Officer, AICTE", nullable=False)
    joint_holder = Column(String(255), nullable=True)
    instrument_type = Column(String(50), default="Fixed Deposit Receipt", nullable=False)
    is_auto_renewal = Column(Boolean, default=False)

    # Chaining & Lifecycle History (Replacement & Renewal)
    previous_fdr_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="SET NULL"), nullable=True)
    replacement_fdr_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="SET NULL"), nullable=True)

    # Workflow & Intelligence States
    ocr_status = Column(String(50), default="PENDING", nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED, MANUALLY_ENTERED
    verification_status = Column(String(50), default="UNVERIFIED", nullable=False)  # UNVERIFIED, PASSED, PASSED_WITH_WARNINGS, DISCREPANCY_DETECTED, REQUIRES_MANUAL_SCRUTINY
    lifecycle_status = Column(String(50), default="DRAFT", nullable=False, index=True) # DRAFT, SUBMITTED, UNDER_SCRUTINY, APPROVED_ACTIVE, RENEWAL_DUE, etc.

    # Scrutiny Remarks
    scrutiny_remarks = Column(Text, nullable=True)
    authority_remarks = Column(Text, nullable=True)

    # Timestamps
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    institution = relationship("Institution", backref="fdr_records")
    submitted_by = relationship("User", backref="submitted_fdrs")
    documents = relationship("FDRDocument", back_populates="fdr", cascade="all, delete-orphan")


class FDRDocument(Base):
    __tablename__ = "fdr_documents"

    id = Column(Integer, primary_key=True, index=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="CASCADE"), nullable=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    document_type = Column(String(50), default="FDR_INSTRUMENT", nullable=False) # FDR_INSTRUMENT, BANK_CONFIRMATION, RENEWAL_COPY, SUPPORTING
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    fdr = relationship("FDRRecord", back_populates="documents")
    institution = relationship("Institution")
    uploaded_by = relationship("User")
