from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict

class OCRCorrectionRequest(BaseModel):
    corrected_fields: Dict[str, Any]

class OCRExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fdr_id: int
    document_id: int
    raw_text: str
    extracted_fields: Dict[str, Any]
    field_confidences: Dict[str, float]
    overall_confidence: float
    processing_engine: str
    processing_time_ms: Optional[int] = None
    is_reviewed: int
    reviewed_at: Optional[datetime] = None
    created_at: datetime

