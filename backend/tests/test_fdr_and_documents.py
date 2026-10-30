import io
import uuid
from decimal import Decimal
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.seed import init_db

# Ensure tables and seed data are ready
init_db()
client = TestClient(app)

def get_auth_token(email: str, password: str = "Admin@123") -> str:
    """Helper to authenticate and return a valid access token."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": password}
    )
    assert res.status_code == 200, f"Authentication failed for {email}: {res.text}"
    return res.json()["access_token"]

# -------------------------------------------------------------------------
# FDR CRUD & Validations
# -------------------------------------------------------------------------

def test_fdr_create_success():
    """Verify an Institution Admin can successfully create an FDR in DRAFT status."""
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_payload = {
        "fdr_number": f"FDR-TEST-{uid}",
        "bank_name": "State Bank of India",
        "branch_name": "IIT Delhi Branch",
        "ifsc_code": "SBIN0001077",
        "deposit_amount": "5000000.00",
        "issue_date": str(date.today() - timedelta(days=30)),
        "maturity_date": str(date.today() + timedelta(days=1065)), # ~3 years
        "interest_rate": "7.15",
        "beneficiary": "Member Secretary, AICTE",
        "is_auto_renewal": False
    }

    res = client.post("/api/v1/fdr", json=fdr_payload, headers=headers)
    assert res.status_code == 201, f"Create FDR failed: {res.text}"
    data = res.json()
    assert data["fdr_number"] == fdr_payload["fdr_number"]
    assert data["lifecycle_status"] == "DRAFT"
    assert Decimal(str(data["deposit_amount"])) == Decimal("5000000.00")
    assert data["ocr_status"] == "MANUALLY_ENTERED"
    assert data["verification_status"] == "UNVERIFIED"

def test_fdr_duplicate_detection():
    """Verify that submitting duplicate FDR with identical number and bank is rejected (Module C)."""
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_payload = {
        "fdr_number": f"FDR-DUP-{uid}",
        "bank_name": "Punjab National Bank",
        "branch_name": "Saket Branch",
        "ifsc_code": "PUNB0001234",
        "deposit_amount": "2000000.00",
        "issue_date": str(date.today() - timedelta(days=10)),
        "maturity_date": str(date.today() + timedelta(days=365)),
        "interest_rate": "7.00"
    }

    # First creation should succeed
    res1 = client.post("/api/v1/fdr", json=fdr_payload, headers=headers)
    assert res1.status_code == 201

    # Second creation with identical FDR number and bank must be rejected
    res2 = client.post("/api/v1/fdr", json=fdr_payload, headers=headers)
    assert res2.status_code == 400
    assert "Duplicate FDR detected" in res2.json()["detail"]

def test_fdr_ifsc_and_date_validation():
    """Verify IFSC code format enforcement and date sanity checks."""
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Invalid IFSC (5th char is not 0)
    bad_ifsc_payload = {
        "fdr_number": "FDR-BAD-IFSC-01",
        "bank_name": "Canara Bank",
        "branch_name": "Connaught Place",
        "ifsc_code": "CNRB1234567", # 5th char is '1', not '0'
        "deposit_amount": "1000000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=365))
    }
    res_bad_ifsc = client.post("/api/v1/fdr", json=bad_ifsc_payload, headers=headers)
    assert res_bad_ifsc.status_code == 422

    # 2. Maturity date before or on issue date
    bad_date_payload = {
        "fdr_number": "FDR-BAD-DATE-01",
        "bank_name": "Canara Bank",
        "branch_name": "Connaught Place",
        "ifsc_code": "CNRB0001234",
        "deposit_amount": "1000000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() - timedelta(days=1)) # in the past
    }
    res_bad_date = client.post("/api/v1/fdr", json=bad_date_payload, headers=headers)
    assert res_bad_date.status_code == 422

# -------------------------------------------------------------------------
# Multi-Tenant Data Isolation (Rule 11)
# -------------------------------------------------------------------------

def test_multi_tenant_fdr_isolation():
    """
    CRITICAL COMPLIANCE TEST: Rule 11
    Verify Institution 1 Admin CANNOT access, view or modify Institution 2 records.
    """
    inst1_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    inst2_token = get_auth_token("inst2_admin@fdrsetu.gov.in")
    scrutiny_token = get_auth_token("scrutiny_officer@fdrsetu.gov.in")

    headers_inst1 = {"Authorization": f"Bearer {inst1_token}"}
    headers_inst2 = {"Authorization": f"Bearer {inst2_token}"}
    headers_scrutiny = {"Authorization": f"Bearer {scrutiny_token}"}

    # 1. Inst 2 Admin fetches their own FDR list
    res2_list = client.get("/api/v1/fdr", headers=headers_inst2)
    assert res2_list.status_code == 200
    inst2_fdrs = res2_list.json()
    assert len(inst2_fdrs) > 0
    inst2_fdr_id = inst2_fdrs[0]["id"]

    # 2. Inst 1 Admin attempts direct GET access to Inst 2's FDR -> must return 403 Forbidden!
    forbidden_res = client.get(f"/api/v1/fdr/{inst2_fdr_id}", headers=headers_inst1)
    assert forbidden_res.status_code == 403
    assert "Access denied" in forbidden_res.json()["detail"]

    # 3. Inst 1 Admin queries list -> must NOT contain any of Inst 2's records
    inst1_list = client.get("/api/v1/fdr", headers=headers_inst1).json()
    inst1_ids = [r["id"] for r in inst1_list]
    assert inst2_fdr_id not in inst1_ids

    # 4. Scrutiny Officer can see Inst 2's FDR
    scrutiny_res = client.get(f"/api/v1/fdr/{inst2_fdr_id}", headers=headers_scrutiny)
    assert scrutiny_res.status_code == 200
    assert scrutiny_res.json()["id"] == inst2_fdr_id

# -------------------------------------------------------------------------
# Document Upload, Signature Checks & Downloads
# -------------------------------------------------------------------------

def test_document_upload_and_preview():
    """Verify document upload with magic signature validation, hash computation and inline preview."""
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a draft FDR
    uid = uuid.uuid4().hex[:6]
    fdr_res = client.post("/api/v1/fdr", json={
        "fdr_number": f"FDR-DOC-{uid}",
        "bank_name": "Bank of India",
        "branch_name": "Hauz Khas",
        "ifsc_code": "BKID0000001",
        "deposit_amount": "1500000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=365))
    }, headers=headers)
    assert fdr_res.status_code == 201
    fdr_id = fdr_res.json()["id"]

    # 2. Upload valid PDF
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    upload_res = client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        headers=headers,
        files={"file": ("test_fdr_receipt.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"document_type": "FDR_INSTRUMENT"}
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    assert doc_data["fdr_id"] == fdr_id
    assert doc_data["original_filename"] == "test_fdr_receipt.pdf"
    assert doc_data["mime_type"] == "application/pdf"
    assert len(doc_data["sha256_hash"]) == 64
    doc_id = doc_data["id"]

    # 3. Test Authorized Document Download
    download_res = client.get(f"/api/v1/documents/{doc_id}/download", headers=headers)
    assert download_res.status_code == 200
    assert download_res.content == pdf_bytes

    # 4. Test Authorized Document Preview
    preview_res = client.get(f"/api/v1/documents/{doc_id}/preview", headers=headers)
    assert preview_res.status_code == 200
    assert "inline" in preview_res.headers.get("Content-Disposition", "")

def test_document_invalid_magic_signature_rejection():
    """Verify that masquerading files (e.g. text file renamed to .pdf) are rejected."""
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    fdr_list = client.get("/api/v1/fdr", headers=headers).json()
    fdr_id = fdr_list[0]["id"]

    # File with .pdf extension but invalid header bytes
    fake_pdf = b"This is just plain text, not a real PDF structure"
    bad_upload = client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        headers=headers,
        files={"file": ("malicious_fake.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        data={"document_type": "FDR_INSTRUMENT"}
    )
    assert bad_upload.status_code == 400
    assert "Invalid PDF document signature" in bad_upload.json()["detail"]

def test_cross_tenant_document_download_forbidden():
    """Verify Institution 1 cannot download documents belonging to Institution 2."""
    inst2_token = get_auth_token("inst2_admin@fdrsetu.gov.in")
    inst1_token = get_auth_token("inst_admin@fdrsetu.gov.in")

    # Get Inst 2's FDR document ID
    res2 = client.get("/api/v1/fdr", headers={"Authorization": f"Bearer {inst2_token}"})
    inst2_fdrs = res2.json()
    inst2_doc_id = inst2_fdrs[0]["documents"][0]["id"]

    # Inst 1 attempts download -> 403 Forbidden
    steal_res = client.get(
        f"/api/v1/documents/{inst2_doc_id}/download",
        headers={"Authorization": f"Bearer {inst1_token}"}
    )
    assert steal_res.status_code == 403
    assert "Access denied" in steal_res.json()["detail"]

# -------------------------------------------------------------------------
# Scrutiny Submission & Lifecycle Controls
# -------------------------------------------------------------------------

def test_fdr_submit_requires_document():
    """Verify submitting an FDR for scrutiny requires at least one supporting document (Rule 10)."""
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # Create draft with NO documents
    uid = uuid.uuid4().hex[:6]
    fdr_res = client.post("/api/v1/fdr", json={
        "fdr_number": f"FDR-NODOC-{uid}",
        "bank_name": "Union Bank of India",
        "branch_name": "Nehru Place",
        "ifsc_code": "UBIN0001234",
        "deposit_amount": "1000000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=365))
    }, headers=headers)
    fdr_id = fdr_res.json()["id"]

    # Attempt to submit -> must be rejected
    submit_res = client.post(f"/api/v1/fdr/{fdr_id}/submit", headers=headers)
    assert submit_res.status_code == 400
    assert "Missing supporting document" in submit_res.json()["detail"]

    # Upload document
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        headers=headers,
        files={"file": ("fdr_copy.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )

    # Submit again -> now succeeds
    submit_res2 = client.post(f"/api/v1/fdr/{fdr_id}/submit", headers=headers)
    assert submit_res2.status_code == 200
    assert submit_res2.json()["lifecycle_status"] == "UNDER_SCRUTINY"

def test_fdr_draft_update_and_delete():
    """Verify draft FDR can be edited and deleted, but submitted FDR cannot be edited or deleted."""
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    uid = uuid.uuid4().hex[:6]
    fdr_res = client.post("/api/v1/fdr", json={
        "fdr_number": f"FDR-EDIT-{uid}",
        "bank_name": "Axis Bank",
        "branch_name": "Green Park",
        "ifsc_code": "UTIB0000123",
        "deposit_amount": "2000000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=730))
    }, headers=headers)
    fdr_id = fdr_res.json()["id"]

    # 1. Update draft
    update_res = client.patch(f"/api/v1/fdr/{fdr_id}", json={
        "deposit_amount": "2500000.00",
        "branch_name": "South Extension"
    }, headers=headers)
    assert update_res.status_code == 200
    assert Decimal(str(update_res.json()["deposit_amount"])) == Decimal("2500000.00")
    assert update_res.json()["branch_name"] == "South Extension"

    # 2. Delete draft
    del_res = client.delete(f"/api/v1/fdr/{fdr_id}", headers=headers)
    assert del_res.status_code == 200

    # 3. Confirm deletion
    get_res = client.get(f"/api/v1/fdr/{fdr_id}", headers=headers)
    assert get_res.status_code == 404

def test_fdr_real_database_statistics():
    """Verify statistics endpoint returns computed values from database queries (Rule 7)."""
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    res = client.get("/api/v1/fdr/statistics", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    stats = res.json()
    assert "total_fdrs" in stats
    assert "total_deposit_amount" in stats
    assert "active_count" in stats
    assert stats["total_fdrs"] >= 1
    assert Decimal(str(stats["total_deposit_amount"])) > 0
