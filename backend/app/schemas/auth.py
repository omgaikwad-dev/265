from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class LoginRequest(BaseModel):
    username_or_email: str = Field(..., description="Email address or username")
    password: str = Field(..., min_length=6, description="Account password")

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str] = None

class InstitutionBriefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    aicte_id: str
    name: str
    state: str
    account_status: str

class UserProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    username: str
    full_name: str
    phone_number: Optional[str] = None
    designation: Optional[str] = None
    is_active: bool
    role: RoleOut
    institution: Optional[InstitutionBriefOut] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserProfileOut

class RegisterInstitutionRequest(BaseModel):
    # Institution details
    aicte_id: str = Field(..., min_length=5, max_length=50, description="Official AICTE permanent/application ID")
    name: str = Field(..., min_length=3, max_length=255, description="Full institution name")
    institution_type: Optional[str] = "Engineering & Technology"
    address: str = Field(..., min_length=5, description="Physical campus address")
    state: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=100)
    pin_code: Optional[str] = None
    official_email: EmailStr
    phone_number: str = Field(..., min_length=8, max_length=20)
    
    # Institution Administrator user details
    admin_name: str = Field(..., min_length=2, max_length=150)
    admin_username: str = Field(..., min_length=3, max_length=50)
    admin_email: EmailStr
    admin_phone: Optional[str] = None
    admin_designation: Optional[str] = "Institution FDR Administrator"
    password: str = Field(..., min_length=6, description="Secure account password")
