from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

# -------------------------------------------------------------------------
# Rules Schemas
# -------------------------------------------------------------------------
class VerificationRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_code: str
    name: str
    description: str
    severity: str
    is_enabled: bool
    parameters: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class VerificationRuleUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    severity: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

# -------------------------------------------------------------------------
# Verification Report Schemas
# -------------------------------------------------------------------------
class RuleResultItem(BaseModel):
    rule_code: str
    name: str
    severity: str
    status: str  # PASSED, WARNING, FAILED, SKIPPED
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None

class VerificationReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fdr_id: int
    overall_status: str  # PASSED, PASSED_WITH_WARNINGS, FAILED_DISCREPANCIES
    total_rules_evaluated: int
    passed_count: int
    warning_count: int
    failed_count: int
    rule_results: List[Dict[str, Any]]
    evaluated_by_id: Optional[int] = None
    created_at: datetime

# -------------------------------------------------------------------------
# Discrepancy Schemas
# -------------------------------------------------------------------------
class DiscrepancyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fdr_id: int
    report_id: Optional[int] = None
    rule_code: str
    severity: str
    title: str
    description: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    status: str
    raised_by_role: str
    raised_by_user_id: Optional[int] = None
    institution_response: Optional[str] = None
    responded_at: Optional[datetime] = None
    officer_resolution_note: Optional[str] = None
    resolved_by_user_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

class DiscrepancyCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    severity: str = "HIGH"
    rule_code: str = "SCRUTINY_OFFICER_OBSERVATION"
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None

class DiscrepancyResponse(BaseModel):
    response_text: str = Field(..., min_length=3)

class DiscrepancyResolve(BaseModel):
    resolution_note: str = Field(..., min_length=3)
    status: str = "RESOLVED"  # RESOLVED or WAIVED

class ScrutinyRecommendationRequest(BaseModel):
    recommendation: str  # RECOMMEND_APPROVAL, RECOMMEND_REJECTION, NEED_MORE_DOCUMENTS
    remarks: str = Field(..., min_length=3)
