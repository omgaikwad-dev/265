from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.lifecycle.service import LifecycleService
from app.schemas.fdr import FDROut, FDRCreate

router = APIRouter(tags=["FDR Lifecycle & Maturity Monitoring"])

@router.post("/lifecycle/scan-maturities")
def scan_and_update_fdr_maturities(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    On-demand operational trigger to execute the maturity monitoring scan across the database.
    Evaluates maturity dates, transitions <= 90 days to RENEWAL_DUE and <= 0 days to MATURED.
    """
    return LifecycleService.scan_and_update_maturities(
        db, trigger_source="ON_DEMAND_API", triggered_by_user=current_user
    )


@router.get("/lifecycle/maturity-timeline")
def get_fdr_maturity_timeline(
    institution_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves dynamic calendar timeline analytics, grouping active FDRs into maturity buckets:
    OVERDUE_MATURED, WITHIN_7_DAYS, WITHIN_30_DAYS, WITHIN_60_DAYS, WITHIN_90_DAYS, HEALTHY_ACTIVE.
    """
    return LifecycleService.get_maturity_timeline(db, current_user, institution_id)


@router.post("/fdr/{fdr_id}/renew", response_model=FDROut, status_code=status.HTTP_201_CREATED)
def initiate_fdr_renewal(
    fdr_id: int,
    renewal_payload: FDRCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiates an instrument renewal linked to an existing FDR (previous_fdr_id).
    Marks original FDR as RENEWAL_SUBMITTED and creates new draft instrument in the lineage chain.
    """
    client_ip = request.client.host if request.client else None
    return LifecycleService.initiate_renewal(
        db, fdr_id, renewal_payload.model_dump(), current_user, client_ip
    )


@router.get("/fdr/{fdr_id}/renewal-history")
def get_fdr_renewal_history(
    fdr_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Traverses and returns the complete immutable chain of previous and renewed FDR instruments.
    """
    return LifecycleService.get_renewal_lineage(db, fdr_id, current_user)
