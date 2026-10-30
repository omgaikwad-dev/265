from typing import List, Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.verification.service import VerificationService
from app.schemas.verification import (
    VerificationRuleOut,
    VerificationRuleUpdate,
    VerificationReportOut,
    DiscrepancyOut,
    DiscrepancyCreate,
    DiscrepancyResponse,
    DiscrepancyResolve,
    ScrutinyRecommendationRequest
)
from app.schemas.fdr import FDROut

router = APIRouter(tags=["Verification & Scrutiny Engine"])

# -------------------------------------------------------------------------
# Verification Execution & Reports
# -------------------------------------------------------------------------
@router.post("/fdr/{fdr_id}/verify", response_model=VerificationReportOut)
def run_fdr_verification(
    fdr_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes the 12-rule Intelligent Verification Engine on the FDR instrument.
    Generates report and records discrepancies for any failed/warning rules.
    """
    client_ip = request.client.host if request.client else None
    return VerificationService.run_verification(db, fdr_id, current_user, client_ip)


@router.get("/fdr/{fdr_id}/verification-report", response_model=Optional[VerificationReportOut])
def get_latest_verification_report(
    fdr_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves the latest verification scorecard and detailed rule breakdown."""
    return VerificationService.get_latest_report(db, fdr_id, current_user)


# -------------------------------------------------------------------------
# Discrepancies & Scrutiny Observations
# -------------------------------------------------------------------------
@router.get("/fdr/{fdr_id}/discrepancies", response_model=List[DiscrepancyOut])
def list_fdr_discrepancies(
    fdr_id: int,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all open, resolved, or waived discrepancies for an FDR."""
    return VerificationService.get_discrepancies(db, fdr_id, current_user, status)


@router.post("/fdr/{fdr_id}/discrepancies", response_model=DiscrepancyOut, status_code=status.HTTP_201_CREATED)
def raise_manual_scrutiny_discrepancy(
    fdr_id: int,
    discrepancy_data: DiscrepancyCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows AICTE Scrutiny Officer to raise custom scrutiny observations."""
    client_ip = request.client.host if request.client else None
    return VerificationService.raise_manual_discrepancy(
        db, fdr_id, discrepancy_data.model_dump(), current_user, client_ip
    )


@router.post("/discrepancies/{discrepancy_id}/respond", response_model=DiscrepancyOut)
def respond_to_discrepancy(
    discrepancy_id: int,
    response_payload: DiscrepancyResponse,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows Technical Institution to submit a formal clarification/response to an observation."""
    client_ip = request.client.host if request.client else None
    return VerificationService.respond_to_discrepancy(
        db, discrepancy_id, response_payload.response_text, current_user, client_ip
    )


@router.post("/discrepancies/{discrepancy_id}/resolve", response_model=DiscrepancyOut)
def resolve_discrepancy(
    discrepancy_id: int,
    resolve_payload: DiscrepancyResolve,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows AICTE Scrutiny Officer to mark a discrepancy as RESOLVED or WAIVED."""
    client_ip = request.client.host if request.client else None
    return VerificationService.resolve_discrepancy(
        db, discrepancy_id, resolve_payload.resolution_note, resolve_payload.status, current_user, client_ip
    )


@router.post("/fdr/{fdr_id}/scrutiny-recommendation", response_model=FDROut)
def submit_scrutiny_recommendation(
    fdr_id: int,
    rec_payload: ScrutinyRecommendationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows Scrutiny Officer to record recommendation (RECOMMEND_APPROVAL, RECOMMEND_REJECTION, NEED_MORE_DOCUMENTS)."""
    client_ip = request.client.host if request.client else None
    return VerificationService.record_scrutiny_recommendation(
        db, fdr_id, rec_payload.recommendation, rec_payload.remarks, current_user, client_ip
    )


# -------------------------------------------------------------------------
# Rule Administration
# -------------------------------------------------------------------------
@router.get("/verification/rules", response_model=List[VerificationRuleOut])
def list_verification_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all configurable verification rules."""
    return VerificationService.get_all_rules(db)


@router.patch("/verification/rules/{rule_id}", response_model=VerificationRuleOut)
def update_verification_rule(
    rule_id: int,
    update_data: VerificationRuleUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Allows System Administrator to toggle rules and configure threshold parameters."""
    client_ip = request.client.host if request.client else None
    return VerificationService.update_rule(
        db, rule_id, update_data.model_dump(exclude_unset=True), current_user, client_ip
    )
