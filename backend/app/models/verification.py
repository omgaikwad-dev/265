from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class VerificationRule(Base):
    __tablename__ = "verification_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="HIGH", nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    is_enabled = Column(Boolean, default=True, nullable=False)
    parameters = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class VerificationReport(Base):
    __tablename__ = "verification_reports"

    id = Column(Integer, primary_key=True, index=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_status = Column(String(30), nullable=False)  # PASSED, PASSED_WITH_WARNINGS, FAILED_DISCREPANCIES
    total_rules_evaluated = Column(Integer, default=12, nullable=False)
    passed_count = Column(Integer, default=0, nullable=False)
    warning_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    rule_results = Column(JSON, default=list, nullable=False)
    evaluated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    fdr = relationship("FDRRecord", backref="verification_reports")
    discrepancies = relationship("Discrepancy", back_populates="report", cascade="all, delete-orphan")


class Discrepancy(Base):
    __tablename__ = "discrepancies"

    id = Column(Integer, primary_key=True, index=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("verification_reports.id", ondelete="SET NULL"), nullable=True, index=True)
    rule_code = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), default="HIGH", nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    expected_value = Column(String(255), nullable=True)
    actual_value = Column(String(255), nullable=True)
    status = Column(String(30), default="OPEN", nullable=False, index=True)  # OPEN, RESOLVED, WAIVED
    raised_by_role = Column(String(50), default="SYSTEM_VERIFICATION_ENGINE", nullable=False)
    raised_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    institution_response = Column(Text, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    officer_resolution_note = Column(Text, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    fdr = relationship("FDRRecord", backref="discrepancies")
    report = relationship("VerificationReport", back_populates="discrepancies")
