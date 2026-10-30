import io
import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.seed import init_db

init_db()
client = TestClient(app)

MINIMAL_VALID_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"

def get_auth_token(email="inst_admin@fdrsetu.gov.in", password="Admin@123"):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": password}
    )
    assert login_res.status_code == 200
    return login_res.json()["access_token"], login_res.json()["user"]

def test_create_fdr_draft():
    """Verify that an Institution Admin can create a draft FDR record."""
    token, user = get_auth_token("inst_admin@fdrsetu.gov.in")
    suffix = uuid.uuid4().hex[:6]
    fdr_number = f"FDR-TEST-{suffix}"

    payload = {
        "fdr_number": fdr_number,
        "bank_name": "State Bank of India",
        "branch_name": "Vasant Kunj Branch",
        "ifsc_code": "SBIN0001234",
        "deposit_amount": 1500000.00,
        "issue_date": "2026-01-15",
        "maturity_date": "2029-01-14",
        "interest_rate": 7.15,
        "beneficiary": "Member Secretary, AICTE / Regional Officer, AICTE",
        "joint_holder": "Delhi Institute of Tech",
        "instrument_type": "Fixed Deposit Receipt",
        "is_auto_renewal": False
    }

    res = client.post(
        "/api/v1/fdr",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["fdr_number"] == fdr_number
    assert float(data["deposit_amount"]) == 1500000.00
    assert data["lifecycle_status"] == "DRAFT"
    assert data["ocr_status"] == "MANUALLY_ENTERED"
    assert data["verification_status"] == "UNVERIFIED"

def test_duplicate_fdr_rejected():
    """Verify that submitting duplicate FDR numbers with the same bank is rejected."""
    token, _ = get_auth_token("inst_admin@fdrsetu.gov.in")
    suffix = uuid.uuid4().hex[:6]
    fdr_number = f"FDR-DUP-{suffix}"

    payload = {
        "fdr_number": fdr_number,
        "bank_name": "Bank of Baroda",
        "branch_name": "Saket Branch",
        "ifsc_code": "BARB0005544",
        "deposit_amount": 500000.00,
        "issue_date": "2026-02-01",
        "maturity_date": "2028-01-31"
    }

    res1 = client.post("/api/v1/fdr", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 201

    res2 = client.post("/api/v1/fdr", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 400
    assert "Duplicate FDR detected" in res2.json()["detail"]

def test_invalid_ifsc_and_dates_rejected():
    """Verify IFSC format and maturity > issue date constraints."""
    token, _ = get_auth_token("inst_admin@fdrsetu.gov.in")

    # Invalid IFSC (5th char not '0')
    bad_ifsc_payload = {
        "fdr_number": f"FDR-BAD-{uuid.uuid4().hex[:4]}",
        "bank_name": "Canara Bank",
        "branch_name": "Main Branch",
        "ifsc_code": "CNRB1234567",
        "deposit_amount": 100000.00,
        "issue_date": "2026-01-01",
        "maturity_date": "2027-01-01"
    }
    res_ifsc = client.post("/api/v1/fdr", json=bad_ifsc_payload, headers={"Authorization": f"Bearer {token}"})
    assert res_ifsc.status_code == 422

    # Invalid dates (maturity before issue)
    bad_dates_payload = {
        "fdr_number": f"FDR-BAD-{uuid.uuid4().hex[:4]}",
        "bank_name": "Canara Bank",
        "branch_name": "Main Branch",
        "ifsc_code": "CNRB0001234",
        "deposit_amount": 100000.00,
        "issue_date": "2026-05-01",
        "maturity_date": "2026-01-01"
    }
    res_date = client.post("/api/v1/fdr", json=bad_dates_payload, headers={"Authorization": f"Bearer {token}"})
    assert res_date.status_code == 422

def test_document_upload_and_magic_bytes():
    """Verify document upload, magic byte check, and rejection of spoofed files."""
    token, _ = get_auth_token("inst_admin@fdrsetu.gov.in")

    # 1. Create a draft FDR
    fdr_res = client.post(
        "/api/v1/fdr",
        json={
            "fdr_number": f"FDR-DOC-{uuid.uuid4().hex[:6]}",
            "bank_name": "Punjab National Bank",
            "branch_name": "Connaught Place",
            "ifsc_code": "PUNB0001234",
            "deposit_amount": 750000.00,
            "issue_date": "2026-03-01",
            "maturity_date": "2029-02-28"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    fdr_id = fdr_res.json()["id"]

    # 2. Upload valid PDF
    valid_pdf_file = io.BytesIO(MINIMAL_VALID_PDF)
    upload_res = client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        files={"file": ("fdr_certificate.pdf", valid_pdf_file, "application/pdf")},
        data={"document_type": "FDR_INSTRUMENT"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    assert doc_data["fdr_id"] == fdr_id
    assert doc_data["mime_type"] == "application/pdf"
    assert "sha256_hash" in doc_data
    doc_id = doc_data["id"]

    # 3. Upload spoofed file (text named as .pdf) -> rejected by magic byte validator
    fake_pdf_file = io.BytesIO(b"This is a plain text file pretending to be PDF")
    fake_res = client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        files={"file": ("malicious.pdf", fake_pdf_file, "application/pdf")},
        data={"document_type": "FDR_INSTRUMENT"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert fake_res.status_code == 400
    assert "Invalid PDF document signature" in fake_res.json()["detail"]

    # 4. Download valid document
    dl_res = client.get(
        f"/api/v1/documents/{doc_id}/download",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert dl_res.status_code == 200
    assert dl_res.content == MINIMAL_VALID_PDF

def test_scrutiny_submission_requires_document():
    """Verify that an FDR cannot be submitted for scrutiny without at least one document (Rule 10)."""
    token, _ = get_auth_token("inst_admin@fdrsetu.gov.in")

    # 1. Create draft without document
    fdr_res = client.post(
        "/api/v1/fdr",
        json={
            "fdr_number": f"FDR-SCRUT-{uuid.uuid4().hex[:6]}",
            "bank_name": "HDFC Bank",
            "branch_name": "Hauz Khas",
            "ifsc_code": "HDFC0001234",
            "deposit_amount": 2000000.00,
            "issue_date": "2026-04-01",
            "maturity_date": "2029-03-31"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    fdr_id = fdr_res.json()["id"]

    # 2. Attempt submit -> rejected
    sub_res = client.post(
        f"/api/v1/fdr/{fdr_id}/submit",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert sub_res.status_code == 400
    assert "Missing supporting document" in sub_res.json()["detail"]

    # 3. Attach valid document
    client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        files={"file": ("cert.pdf", io.BytesIO(MINIMAL_VALID_PDF), "application/pdf")},
        data={"document_type": "FDR_INSTRUMENT"},
        headers={"Authorization": f"Bearer {token}"}
    )

    # 4. Submit again -> succeeds
    sub_success = client.post(
        f"/api/v1/fdr/{fdr_id}/submit",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert sub_success.status_code == 200
    assert sub_success.json()["lifecycle_status"] == "UNDER_SCRUTINY"

def test_fdr_tenant_isolation():
    """Verify multi-tenant isolation: Institution Admin cannot access other institution FDRs (Rule 11)."""
    inst1_token, _ = get_auth_token("inst_admin@fdrsetu.gov.in")

    # 1. Create a second institution and user
    suffix = uuid.uuid4().hex[:5]
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "aicte_id": f"AICTE-ISO-{suffix}",
            "name": f"Isolated College of Engineering {suffix}",
            "institution_type": "Engineering & Technology",
            "address": "Pune Campus",
            "state": "Maharashtra",
            "district": "Pune",
            "official_email": f"iso_{suffix}@college.edu.in",
            "phone_number": "+91 20 2567 8901",
            "admin_name": "Prof. A. Patil",
            "admin_username": f"patil_{suffix}",
            "admin_email": f"patil_{suffix}@college.edu.in",
            "password": "Password@123"
        }
    )
    assert reg_res.status_code == 201
    inst2_token, _ = get_auth_token(f"patil_{suffix}", "Password@123")

    # 2. Institution 2 creates an FDR
    inst2_fdr_res = client.post(
        "/api/v1/fdr",
        json={
            "fdr_number": f"FDR-INST2-{suffix}",
            "bank_name": "Bank of Maharashtra",
            "branch_name": "Shivajinagar",
            "ifsc_code": "MAHB0001234",
            "deposit_amount": 1000000.00,
            "issue_date": "2026-01-01",
            "maturity_date": "2029-01-01"
        },
        headers={"Authorization": f"Bearer {inst2_token}"}
    )
    assert inst2_fdr_res.status_code == 201
    inst2_fdr_id = inst2_fdr_res.json()["id"]

    # 3. Institution 1 attempts to fetch Institution 2's FDR -> rejected with 403 Forbidden
    cross_access_res = client.get(
        f"/api/v1/fdr/{inst2_fdr_id}",
        headers={"Authorization": f"Bearer {inst1_token}"}
    )
    assert cross_access_res.status_code == 403
    assert "Cannot access FDR record belonging to another institution" in cross_access_res.json()["detail"]

    # 4. AICTE Scrutiny Officer CAN view Institution 2's FDR
    so_token, _ = get_auth_token("scrutiny_officer@fdrsetu.gov.in")
    so_res = client.get(
        f"/api/v1/fdr/{inst2_fdr_id}",
        headers={"Authorization": f"Bearer {so_token}"}
    )
    assert so_res.status_code == 200
    assert so_res.json()["id"] == inst2_fdr_id

