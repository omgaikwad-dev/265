from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.fdr import FDROut

class ReleaseRequestCreate(BaseModel):
    release_reason: str = Field(..., min_length=5, description="Justification for security deposit release or refund")
    refund_bank_name: str = Field(..., min_length=2)
    refund_account_number: str = Field(..., min_length=5)
    refund_ifsc: str = Field(..., min_length=11, max_length=11)
    refund_beneficiary_name: str = Field(..., min_length=3)
    noc_document_id: Optional[int] = None

class ReleaseRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fdr_id: int
    institution_id: int
    release_reason: str
    refund_bank_name: str
    refund_account_number: str
    refund_ifsc: str
    refund_beneficiary_name: str
    noc_document_id: Optional[int] = None
    status: str
    authority_remarks: Optional[str] = None
    authorization_reference: Optional[str] = None
    decided_by_id: Optional[int] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class AuthorityFDRDecision(BaseModel):
    decision: str = Field(..., description="APPROVE_FDR or REJECT_FDR")
    remarks: str = Field(..., min_length=3, description="Statutory remarks and conditions of decision")

class AuthorityReleaseDecision(BaseModel):
    decision: str = Field(..., description="APPROVE_RELEASE or REJECT_RELEASE")
    remarks: str = Field(..., min_length=3, description="Official remarks and authorization notes")

class ApprovalQueueOut(BaseModel):
    pending_scrutiny_fdrs: List[FDROut]
    pending_releases: List[ReleaseRequestOut]
    counts: Dict[str, int]

