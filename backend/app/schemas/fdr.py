from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator

class FDRDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fdr_id: Optional[int] = None
    document_type: str
    original_filename: str
    file_size: int
    mime_type: str
    sha256_hash: str
    created_at: datetime

class FDRBase(BaseModel):
    fdr_number: str = Field(..., min_length=3, max_length=100, description="Unique Fixed Deposit Receipt Number")
    bank_name: str = Field(..., min_length=2, max_length=150, description="Issuing Bank Name")
    branch_name: str = Field(..., min_length=2, max_length=150, description="Issuing Branch Name")
    ifsc_code: str = Field(..., min_length=11, max_length=11, description="11-character Indian Financial System Code")
    deposit_amount: Decimal = Field(..., gt=0, description="Principal Deposit Amount in INR")
    issue_date: date = Field(..., description="Date of FDR Issuance")
    maturity_date: date = Field(..., description="Date of FDR Maturity")
    interest_rate: Optional[Decimal] = Field(None, ge=0, le=100, description="Annual Interest Rate (%)")
    beneficiary: Optional[str] = "Member Secretary, AICTE / Regional Officer, AICTE"
    joint_holder: Optional[str] = None
    instrument_type: Optional[str] = "Fixed Deposit Receipt"
    is_auto_renewal: Optional[bool] = False
    previous_fdr_id: Optional[int] = None
    replacement_fdr_id: Optional[int] = None

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc_format(cls, v: str) -> str:
        clean = v.strip().upper()
        if len(clean) != 11:
            raise ValueError("IFSC code must be exactly 11 characters")
        if clean[4] != "0":
            raise ValueError("Fifth character of IFSC code must be '0'")
        return clean

    @field_validator("maturity_date")
    @classmethod
    def validate_dates(cls, v: date, info) -> date:
        issue = info.data.get("issue_date")
        if issue and v <= issue:
            raise ValueError("Maturity date must be after the issue date")
        return v

class FDRCreate(FDRBase):
    institution_id: Optional[int] = None

class FDRUpdate(BaseModel):
    fdr_number: Optional[str] = None
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    ifsc_code: Optional[str] = None
    deposit_amount: Optional[Decimal] = None
    issue_date: Optional[date] = None
    maturity_date: Optional[date] = None
    interest_rate: Optional[Decimal] = None
    beneficiary: Optional[str] = None
    joint_holder: Optional[str] = None
    is_auto_renewal: Optional[bool] = None
    previous_fdr_id: Optional[int] = None
    replacement_fdr_id: Optional[int] = None

class FDRStatisticsOut(BaseModel):
    total_fdrs: int
    total_deposit_amount: Decimal
    active_count: int
    draft_count: int
    under_scrutiny_count: int
    expiring_soon_count: int
    matured_count: int
    total_institutions: Optional[int] = None

class FDROut(FDRBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    institution_id: int
    interest_rate: Optional[Decimal] = None
    ocr_status: str
    verification_status: str
    lifecycle_status: str
    scrutiny_remarks: Optional[str] = None
    authority_remarks: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    documents: List[FDRDocumentOut] = []
    institution_name: Optional[str] = None
    aicte_id: Optional[str] = None
