from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.approval_service import ApprovalService
from app.schemas.release import (
    ReleaseRequestCreate,
    ReleaseRequestOut,
    AuthorityFDRDecision,
    AuthorityReleaseDecision,
    ApprovalQueueOut
)
from app.schemas.fdr import FDROut

router = APIRouter(tags=["Release & Approving Authority Workflows"])

@router.post("/fdr/{fdr_id}/request-release", response_model=ReleaseRequestOut, status_code=status.HTTP_201_CREATED)
def request_fdr_release(
    fdr_id: int,
    release_data: ReleaseRequestCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiates a security deposit release and refund petition for an active or matured FDR.
    Verifies that no unresolved critical compliance discrepancies exist on record.
    """
    client_ip = request.client.host if request.client else None
    return ApprovalService.initiate_release_request(
        db, fdr_id, release_data.model_dump(), current_user, client_ip
    )


@router.get("/fdr/{fdr_id}/release-request", response_model=Optional[ReleaseRequestOut])
def get_fdr_release_request(
    fdr_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves the latest release petition status and authority remarks for an FDR."""
    return ApprovalService.get_fdr_release_request(db, fdr_id, current_user)


@router.get("/approval/queue", response_model=ApprovalQueueOut)
def get_approving_authority_queue(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves cases awaiting statutory executive decision by the AICTE Approving Authority:
    1. Scrutiny cases pending approval/rejection.
    2. Release petitions pending authorization.
    """
    return ApprovalService.get_approval_queue(db, current_user)


@router.post("/fdr/{fdr_id}/authority-decision", response_model=FDROut)
def record_authority_decision_on_fdr(
    fdr_id: int,
    decision_payload: AuthorityFDRDecision,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AICTE Approving Authority statutory sign-off on an FDR under scrutiny (APPROVE_FDR or REJECT_FDR).
    """
    client_ip = request.client.host if request.client else None
    return ApprovalService.authority_decision_on_fdr(
        db, fdr_id, decision_payload.decision, decision_payload.remarks, current_user, client_ip
    )


@router.post("/releases/{release_id}/authority-decision", response_model=ReleaseRequestOut)
def record_authority_decision_on_release(
    release_id: int,
    decision_payload: AuthorityReleaseDecision,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AICTE Approving Authority statutory decision on an eligible release/refund petition (APPROVE_RELEASE or REJECT_RELEASE).
    Generates official Authorization Reference upon approval.
    """
    client_ip = request.client.host if request.client else None
    return ApprovalService.authority_decision_on_release(
        db, release_id, decision_payload.decision, decision_payload.remarks, current_user, client_ip
    )

