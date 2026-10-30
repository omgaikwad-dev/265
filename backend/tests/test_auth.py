import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.seed import init_db

# Ensure DB is seeded before running tests
init_db()
client = TestClient(app)

def test_login_all_five_roles():
    """Verify that all 5 user roles can authenticate successfully and receive JWT tokens."""
    roles_credentials = [
        ("inst_admin@fdrsetu.gov.in", "Admin@123", "ROLE_INSTITUTION_ADMIN"),
        ("scrutiny_officer@fdrsetu.gov.in", "Admin@123", "ROLE_SCRUTINY_OFFICER"),
        ("approving_auth@fdrsetu.gov.in", "Admin@123", "ROLE_APPROVING_AUTHORITY"),
        ("sys_admin@fdrsetu.gov.in", "Admin@123", "ROLE_SYSTEM_ADMIN"),
        ("auditor@fdrsetu.gov.in", "Admin@123", "ROLE_AUDITOR"),
    ]

    for email, password, expected_role in roles_credentials:
        response = client.post(
            "/api/v1/auth/login",
            json={"username_or_email": email, "password": password}
        )
        assert response.status_code == 200, f"Failed login for {email}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email
        assert data["user"]["role"]["name"] == expected_role

def test_login_invalid_password():
    """Verify that incorrect passwords return 401 Unauthorized."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "inst_admin@fdrsetu.gov.in", "password": "WrongPassword!999"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

def test_get_current_user_me_endpoint():
    """Verify /auth/me returns profile when valid Bearer token is provided."""
    # 1. Login to get token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "inst_admin@fdrsetu.gov.in", "password": "Admin@123"}
    )
    token = login_res.json()["access_token"]

    # 2. Query /me with token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == "inst_admin@fdrsetu.gov.in"
    assert user_data["role"]["name"] == "ROLE_INSTITUTION_ADMIN"
    assert user_data["institution"]["name"] is not None

def test_auth_me_unauthorized():
    """Verify /auth/me rejects missing or invalid tokens."""
    res_no_token = client.get("/api/v1/auth/me")
    assert res_no_token.status_code == 401

    res_invalid_token = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"}
    )
    assert res_invalid_token.status_code == 401

def test_refresh_token():
    """Verify refresh token endpoint issues a new valid access token."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "sys_admin@fdrsetu.gov.in", "password": "Admin@123"}
    )
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()

import uuid

def test_institution_registration_workflow():
    """Verify institution self-registration and admin account provisioning."""
    suffix = uuid.uuid4().hex[:6]
    unique_id = f"AICTE-TEST-{suffix}"
    admin_uname = f"ntim_admin_{suffix}"
    admin_mail = f"admin_{suffix}@ntim-mumbai.edu.in"
    reg_payload = {
        "aicte_id": unique_id,
        "name": f"National Technical Institute of Mumbai {suffix}",
        "institution_type": "Engineering & Technology",
        "address": "Bandra Kurla Complex, Mumbai",
        "state": "Maharashtra",
        "district": "Mumbai Suburban",
        "pin_code": "400051",
        "official_email": f"registrar_{suffix}@ntim-mumbai.edu.in",
        "phone_number": "+91 22 2650 1234",
        "admin_name": "Prof. Sanjay Kulkarni",
        "admin_username": admin_uname,
        "admin_email": admin_mail,
        "admin_phone": "+91 99200 11223",
        "admin_designation": "Registrar",
        "password": "SecurePassword@123"
    }

    # Register
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["aicte_id"] == unique_id
    assert "institution_id" in reg_data

    # Verify newly created user can log in immediately
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": admin_uname, "password": "SecurePassword@123"}
    )
    assert login_res.status_code == 200
    assert login_res.json()["user"]["role"]["name"] == "ROLE_INSTITUTION_ADMIN"

    # Duplicate registration attempt should be rejected
    dup_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 400

def test_institution_isolation_enforcement():
    """Verify that Institution Admins cannot access records of other institutions (Rule 11)."""
    # 1. Login as default Institution Admin (mapped to institution 1)
    inst_login = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "inst_admin@fdrsetu.gov.in", "password": "Admin@123"}
    )
    inst_token = inst_login.json()["access_token"]
    my_inst_id = inst_login.json()["user"]["institution"]["id"]

    # Accessing own institution succeeds
    own_res = client.get(
        f"/api/v1/institutions/{my_inst_id}",
        headers={"Authorization": f"Bearer {inst_token}"}
    )
    assert own_res.status_code == 200
    assert own_res.json()["id"] == my_inst_id

    # Accessing another institution ID (e.g. 9999) must be rejected with 403 Forbidden
    other_res = client.get(
        "/api/v1/institutions/9999",
        headers={"Authorization": f"Bearer {inst_token}"}
    )
    assert other_res.status_code == 403
    assert "Cannot access or modify records of another institution" in other_res.json()["detail"]

    # Listing institutions as Institution Admin returns strictly their own institution
    list_inst_res = client.get(
        "/api/v1/institutions",
        headers={"Authorization": f"Bearer {inst_token}"}
    )
    assert list_inst_res.status_code == 200
    inst_list = list_inst_res.json()
    assert len(inst_list) == 1
    assert inst_list[0]["id"] == my_inst_id

    # Listing institutions as Scrutiny Officer can see all institutions
    so_login = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "scrutiny_officer@fdrsetu.gov.in", "password": "Admin@123"}
    )
    so_token = so_login.json()["access_token"]
    so_list_res = client.get(
        "/api/v1/institutions",
        headers={"Authorization": f"Bearer {so_token}"}
    )
    assert so_list_res.status_code == 200
    assert len(so_list_res.json()) >= 1

