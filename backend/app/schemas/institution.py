from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class InstitutionBase(BaseModel):
    aicte_id: str
    name: str
    institution_type: Optional[str] = "Engineering & Technology"
    address: str
    state: str
    district: str
    pin_code: Optional[str] = None
    contact_person: str
    official_email: EmailStr
    phone_number: str

class InstitutionCreate(InstitutionBase):
    pass

class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    pin_code: Optional[str] = None
    contact_person: Optional[str] = None
    phone_number: Optional[str] = None
    account_status: Optional[str] = None

class InstitutionOut(InstitutionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    account_status: str
    registration_date: datetime
    created_at: datetime
