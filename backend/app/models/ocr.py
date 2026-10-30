from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class OCRExtraction(Base):
    __tablename__ = "ocr_extractions"

    id = Column(Integer, primary_key=True, index=True)
    fdr_id = Column(Integer, ForeignKey("fdr_records.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("fdr_documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Raw full text extracted from the document
    raw_text = Column(Text, nullable=False)
    
    # Structured Extracted Fields (JSON dictionary)
    # { "fdr_number": "...", "bank_name": "...", "branch_name": "...", "ifsc_code": "...",
    #   "deposit_amount": 3500000.0, "issue_date": "2024-07-15", "maturity_date": "2027-07-14", ... }
    extracted_fields = Column(JSON, nullable=False)

    # Field-Level Confidence Scores (0.00 to 100.00)
    # { "fdr_number": 96.5, "bank_name": 94.0, "deposit_amount": 98.0, "ifsc_code": 99.0, ... }
    field_confidences = Column(JSON, nullable=False)

    # Overall Document Extraction Confidence
    overall_confidence = Column(Float, nullable=False)

    # Processing Metadata
    processing_engine = Column(String(100), default="PyMuPDF+OpenCV+Tesseract")
    processing_time_ms = Column(Integer, nullable=True)
    
    # Audit & Timestamps
    is_reviewed = Column(Integer, default=0) # 0 = unreviewed, 1 = verified/corrected by user
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    fdr = relationship("FDRRecord", backref="ocr_extractions")
    document = relationship("FDRDocument", backref="ocr_extractions")
    reviewed_by = relationship("User")

