from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.deps import get_current_user
from app.models.user import User, Role
from app.models.institution import Institution
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    RegisterInstitutionRequest,
    UserProfileOut,
)
from app.audit.service import AuditService

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate user with email or username and password.
    Returns JWT access and refresh tokens along with user and institution profile.
    """
    client_ip = request.client.host if request.client else None
    
    # Locate user by email or username
    user = db.query(User).filter(
        (User.email == login_data.username_or_email) | 
        (User.username == login_data.username_or_email)
    ).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        AuditService.log_event(
            db=db,
            action="LOGIN_FAILED",
            entity_type="AUTH",
            details=f"Failed login attempt for identifier: {login_data.username_or_email}",
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: username or password does not match",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        AuditService.log_event(
            db=db,
            action="LOGIN_REJECTED_INACTIVE",
            entity_type="AUTH",
            user_id=user.id,
            username=user.username,
            role=user.role.name if user.role else None,
            details="Login blocked: User account is deactivated",
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your AICTE Administrator.",
        )

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    role_name = user.role.name if user.role else "ROLE_INSTITUTION_ADMIN"

    # Generate JWT tokens
    token_claims = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": role_name,
        "institution_id": user.institution_id
    }
    access_token = create_access_token(data=token_claims)
    refresh_token = create_refresh_token(data=token_claims)

    # Log successful login in immutable audit trail
    AuditService.log_event(
        db=db,
        action="LOGIN_SUCCESS",
        entity_type="AUTH",
        user_id=user.id,
        username=user.username,
        role=role_name,
        details=f"User authenticated successfully into role {role_name}",
        ip_address=client_ip
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_institution(
    reg_data: RegisterInstitutionRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new Institution along with its designated Institution Administrator account.
    """
    client_ip = request.client.host if request.client else None

    # Check for existing institution AICTE ID or official email
    existing_inst = db.query(Institution).filter(
        (Institution.aicte_id == reg_data.aicte_id) |
        (Institution.official_email == reg_data.official_email)
    ).first()
    if existing_inst:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An institution with this AICTE ID or Official Email is already registered.",
        )

    # Check for existing user username or email
    existing_user = db.query(User).filter(
        (User.email == reg_data.admin_email) |
        (User.username == reg_data.admin_username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this administrator email or username already exists.",
        )

    # Fetch Institution Admin role
    inst_role = db.query(Role).filter(Role.name == "ROLE_INSTITUTION_ADMIN").first()
    if not inst_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System configuration error: ROLE_INSTITUTION_ADMIN not found.",
        )

    # Create Institution record
    new_inst = Institution(
        aicte_id=reg_data.aicte_id,
        name=reg_data.name,
        institution_type=reg_data.institution_type or "Engineering & Technology",
        address=reg_data.address,
        state=reg_data.state,
        district=reg_data.district,
        pin_code=reg_data.pin_code,
        contact_person=reg_data.admin_name,
        official_email=reg_data.official_email,
        phone_number=reg_data.phone_number,
        account_status="ACTIVE"
    )
    db.add(new_inst)
    db.flush()

    # Create Admin User record
    new_user = User(
        username=reg_data.admin_username,
        email=reg_data.admin_email,
        full_name=reg_data.admin_name,
        phone_number=reg_data.admin_phone,
        designation=reg_data.admin_designation or "Institution FDR Administrator",
        hashed_password=hash_password(reg_data.password),
        role_id=inst_role.id,
        institution_id=new_inst.id,
        is_active=True,
        is_verified=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_inst)
    db.refresh(new_user)

    # Audit log
    AuditService.log_event(
        db=db,
        action="INSTITUTION_REGISTERED",
        entity_type="INSTITUTION",
        entity_id=str(new_inst.id),
        user_id=new_user.id,
        username=new_user.username,
        role="ROLE_INSTITUTION_ADMIN",
        details=f"New institution {new_inst.name} ({new_inst.aicte_id}) onboarded with admin {new_user.email}",
        ip_address=client_ip
    )

    return {
        "message": "Institution and administrator registered successfully.",
        "institution_id": new_inst.id,
        "aicte_id": new_inst.aicte_id,
        "admin_user_id": new_user.id,
        "admin_email": new_user.email
    }

@router.post("/refresh")
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Issues a new access token using a valid refresh token.
    """
    try:
        payload = decode_token(refresh_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected refresh token"
            )
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is expired or invalid"
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated"
        )

    token_claims = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role.name if user.role else "ROLE_INSTITUTION_ADMIN",
        "institution_id": user.institution_id
    }
    new_access_token = create_access_token(data=token_claims)
    return {"access_token": new_access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserProfileOut)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve current authenticated user profile, roles, and linked institution.
    """
    return current_user

@router.post("/logout")
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Invalidates session and records logout in audit trail.
    """
    client_ip = request.client.host if request.client else None
    AuditService.log_event(
        db=db,
        action="LOGOUT",
        entity_type="AUTH",
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role.name if current_user.role else None,
        details="User logged out gracefully",
        ip_address=client_ip
    )
    return {"message": "Logged out successfully"}

@router.get("/demo-accounts")
def get_demo_accounts():
    """
    Convenience endpoint providing the 5 seeded roles and pre-configured credentials for evaluation.
    """
    from app.core.seed import DEMO_USERS
    return [
        {
            "role_name": u["role_name"],
            "role_title": u["designation"],
            "name": u["full_name"],
            "email": u["email"],
            "username": u["username"],
            "password": "Admin@123",
            "is_institution": u["is_institution_user"]
        }
        for u in DEMO_USERS
    ]
