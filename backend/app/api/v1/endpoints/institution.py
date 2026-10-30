from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, enforce_institution_isolation
from app.models.user import User
from app.models.institution import Institution
from app.schemas.institution import InstitutionOut, InstitutionUpdate, InstitutionCreate
from app.audit.service import AuditService

router = APIRouter()

@router.get("", response_model=List[InstitutionOut])
def get_institutions(
    search: Optional[str] = Query(None, description="Search by name, AICTE ID, or state"),
    state: Optional[str] = Query(None, description="Filter by state"),
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, PENDING, SUSPENDED"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List institutions.
    - AICTE Officers, Admins & Auditors can view all matching institutions.
    - Institution Admins are strictly scoped to their own institution.
    """
    user_role = current_user.role.name if current_user.role else None

    query = db.query(Institution)

    # Institution isolation rule: Institution Admin can only access their own institution record
    if user_role == "ROLE_INSTITUTION_ADMIN":
        if not current_user.institution_id:
            return []
        query = query.filter(Institution.id == current_user.institution_id)
    else:
        if search:
            search_fmt = f"%{search}%"
            query = query.filter(
                (Institution.name.ilike(search_fmt)) |
                (Institution.aicte_id.ilike(search_fmt)) |
                (Institution.state.ilike(search_fmt)) |
                (Institution.official_email.ilike(search_fmt))
            )
        if state:
            query = query.filter(Institution.state.ilike(f"%{state}%"))
        if status:
            query = query.filter(Institution.account_status == status)

    return query.offset(skip).limit(limit).all()

@router.post("", response_model=InstitutionOut, status_code=status.HTTP_201_CREATED)
def create_institution(
    inst_in: InstitutionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new institution record.
    Restricted to System Administrators and AICTE Approving Authorities.
    """
    user_role = current_user.role.name if current_user.role else None
    if user_role not in ["ROLE_SYSTEM_ADMIN", "ROLE_APPROVING_AUTHORITY"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only System Administrators or AICTE Approving Authorities can register institutions directly."
        )

    # Check unique AICTE ID
    existing_aicte = db.query(Institution).filter(Institution.aicte_id == inst_in.aicte_id.strip()).first()
    if existing_aicte:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Institution with AICTE ID '{inst_in.aicte_id}' already exists."
        )

    # Check unique official email
    existing_email = db.query(Institution).filter(Institution.official_email == inst_in.official_email.lower().strip()).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Institution with email '{inst_in.official_email}' already exists."
        )

    new_inst = Institution(
        aicte_id=inst_in.aicte_id.strip(),
        name=inst_in.name.strip(),
        institution_type=inst_in.institution_type or "Engineering & Technology",
        address=inst_in.address.strip(),
        state=inst_in.state.strip(),
        district=inst_in.district.strip(),
        pin_code=inst_in.pin_code.strip() if inst_in.pin_code else None,
        contact_person=inst_in.contact_person.strip(),
        official_email=inst_in.official_email.lower().strip(),
        phone_number=inst_in.phone_number.strip(),
        account_status="ACTIVE"
    )
    db.add(new_inst)
    db.commit()
    db.refresh(new_inst)

    client_ip = request.client.host if request.client else None
    AuditService.log_event(
        db=db,
        action="INSTITUTION_CREATED",
        entity_type="INSTITUTION",
        entity_id=str(new_inst.id),
        user_id=current_user.id,
        username=current_user.username,
        role=user_role,
        new_value={"aicte_id": new_inst.aicte_id, "name": new_inst.name, "state": new_inst.state},
        ip_address=client_ip
    )

    return new_inst

@router.get("/{institution_id}", response_model=InstitutionOut)
def get_institution_by_id(
    institution_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed institution profile.
    Enforces isolation: Institution Admin cannot view other institutions.
    """
    enforce_institution_isolation(institution_id, current_user)

    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution with ID {institution_id} not found"
        )
    return inst

@router.patch("/{institution_id}", response_model=InstitutionOut)
def update_institution(
    institution_id: int,
    update_data: InstitutionUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update institution profile fields.
    """
    enforce_institution_isolation(institution_id, current_user)
    user_role = current_user.role.name if current_user.role else None

    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution with ID {institution_id} not found"
        )

    prev_snapshot = {"name": inst.name, "contact_person": inst.contact_person, "phone_number": inst.phone_number}

    # Only System Admin or AICTE Approving Authority can modify account status
    if update_data.account_status is not None:
        if user_role not in ["ROLE_SYSTEM_ADMIN", "ROLE_APPROVING_AUTHORITY"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only AICTE Authority or System Admin can alter institution account status."
            )
        inst.account_status = update_data.account_status

    if update_data.name:
        inst.name = update_data.name
    if update_data.address:
        inst.address = update_data.address
    if update_data.state:
        inst.state = update_data.state
    if update_data.district:
        inst.district = update_data.district
    if update_data.pin_code:
        inst.pin_code = update_data.pin_code
    if update_data.contact_person:
        inst.contact_person = update_data.contact_person
    if update_data.phone_number:
        inst.phone_number = update_data.phone_number

    db.commit()
    db.refresh(inst)

    client_ip = request.client.host if request.client else None
    AuditService.log_event(
        db=db,
        action="INSTITUTION_UPDATED",
        entity_type="INSTITUTION",
        entity_id=str(inst.id),
        user_id=current_user.id,
        username=current_user.username,
        role=user_role,
        previous_value=prev_snapshot,
        new_value={"name": inst.name, "contact_person": inst.contact_person, "phone_number": inst.phone_number},
        ip_address=client_ip
    )

    return inst
