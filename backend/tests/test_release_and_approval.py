import io
import uuid
from decimal import Decimal
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.seed import init_db

init_db()
client = TestClient(app)

def get_auth_token(email: str, password: str = "Admin@123") -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": password}
    )
    assert res.status_code == 200, f"Authentication failed for {email}: {res.text}"
    return res.json()["access_token"]

VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n"

# -------------------------------------------------------------------------
# Test 1: Approving Authority FDR Approval Workflow
# -------------------------------------------------------------------------
def test_approving_authority_fdr_approval_workflow():
    """Verify that the AICTE Approving Authority can review a scrutinized FDR and grant statutory approval."""
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    authority_token = get_auth_token("approving_auth@fdrsetu.gov.in")

    headers_inst = {"Authorization": f"Bearer {inst_token}"}
    headers_auth = {"Authorization": f"Bearer {authority_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-APPR-{uid}"

    # 1. Institution creates FDR & submits for scrutiny
    res = client.post("/api/v1/fdr", json={
        "fdr_number": fdr_no,
        "bank_name": "State Bank of India",
        "branch_name": "IIT Hauz Khas",
        "ifsc_code": "SBIN0001077",
        "deposit_amount": "5000000.00",
        "issue_date": str(date.today() - timedelta(days=30)),
        "maturity_date": str(date.today() + timedelta(days=1000)),
        "beneficiary": "Member Secretary, AICTE"
    }, headers=headers_inst)
    fdr_id = res.json()["id"]

    client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        data={"document_type": "PRIMARY_INSTRUMENT"},
        files={"file": (f"{fdr_no}.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
        headers=headers_inst
    )
    client.post(f"/api/v1/fdr/{fdr_id}/submit", headers=headers_inst)

    # 2. Approving Authority checks approval queue
    queue_res = client.get("/api/v1/approval/queue", headers=headers_auth)
    assert queue_res.status_code == 200
    queue_data = queue_res.json()
    pending_ids = [f["id"] for f in queue_data["pending_scrutiny_fdrs"]]
    assert fdr_id in pending_ids

    # 3. Approving Authority approves the FDR
    decision_res = client.post(
        f"/api/v1/fdr/{fdr_id}/authority-decision",
        json={
            "decision": "APPROVE_FDR",
            "remarks": "Statutory approval granted for institution affiliation 2026-2027. All security covenants verified."
        },
        headers=headers_auth
    )
    assert decision_res.status_code == 200, decision_res.text
    updated_fdr = decision_res.json()

    assert updated_fdr["lifecycle_status"] == "APPROVED_ACTIVE"
    assert updated_fdr["approved_at"] is not None
    assert "Statutory approval granted" in updated_fdr["authority_remarks"]

# -------------------------------------------------------------------------
# Test 2: Approving Authority FDR Rejection Workflow
# -------------------------------------------------------------------------
def test_approving_authority_fdr_rejection_workflow():
    """Verify that Approving Authority can reject an FDR with official grounds."""
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    authority_token = get_auth_token("approving_auth@fdrsetu.gov.in")

    headers_inst = {"Authorization": f"Bearer {inst_token}"}
    headers_auth = {"Authorization": f"Bearer {authority_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-REJ-{uid}"

    res = client.post("/api/v1/fdr", json={
        "fdr_number": fdr_no,
        "bank_name": "Punjab National Bank",
        "branch_name": "Connaught Place",
        "ifsc_code": "PUNB0001234",
        "deposit_amount": "2000000.00",
        "issue_date": str(date.today() - timedelta(days=10)),
        "maturity_date": str(date.today() + timedelta(days=400)),
        "beneficiary": "Member Secretary, AICTE"
    }, headers=headers_inst)
    fdr_id = res.json()["id"]

    client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        data={"document_type": "PRIMARY_INSTRUMENT"},
        files={"file": (f"{fdr_no}.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
        headers=headers_inst
    )
    client.post(f"/api/v1/fdr/{fdr_id}/submit", headers=headers_inst)

    # Authority rejects
    rej_res = client.post(
        f"/api/v1/fdr/{fdr_id}/authority-decision",
        json={
            "decision": "REJECT_FDR",
            "remarks": "Bank seal is missing and branch manager signature unverified. Instrument rejected."
        },
        headers=headers_auth
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["lifecycle_status"] == "REJECTED"
    assert "Instrument rejected" in rej_res.json()["authority_remarks"]

# -------------------------------------------------------------------------
# Test 3: Release Petition Initiation & Authority Release Authorization
# -------------------------------------------------------------------------
def test_institution_release_petition_and_authority_release_approval():
    """Verify end-to-end release lifecycle: Institution requests release -> Authority authorizes -> Status becomes RELEASED with Authorization Reference."""
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    authority_token = get_auth_token("approving_auth@fdrsetu.gov.in")

    headers_inst = {"Authorization": f"Bearer {inst_token}"}
    headers_auth = {"Authorization": f"Bearer {authority_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-REL-{uid}"

    # 1. Create FDR and mark APPROVED_ACTIVE
    res = client.post("/api/v1/fdr", json={
        "fdr_number": fdr_no,
        "bank_name": "Canara Bank",
        "branch_name": "South Extension",
        "ifsc_code": "CNRB0001234",
        "deposit_amount": "3500000.00",
        "issue_date": str(date.today() - timedelta(days=1100)),
        "maturity_date": str(date.today() - timedelta(days=5)),  # Matured
        "beneficiary": "Member Secretary, AICTE"
    }, headers=headers_inst)
    fdr_id = res.json()["id"]

    # Mark active in DB
    from app.core.database import SessionLocal
    from app.models.fdr import FDRRecord
    db = SessionLocal()
    f = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
    f.lifecycle_status = "APPROVED_ACTIVE"
    db.commit()
    db.close()

    # 2. Institution submits release petition
    release_payload = {
        "release_reason": "Statutory 10-year academic security commitment completed. Applying for refund credit.",
        "refund_bank_name": "Canara Bank",
        "refund_account_number": "009988776655",
        "refund_ifsc": "CNRB0001234",
        "refund_beneficiary_name": "Delhi Institute of Technology Operating A/C"
    }
    rel_res = client.post(f"/api/v1/fdr/{fdr_id}/request-release", json=release_payload, headers=headers_inst)
    assert rel_res.status_code == 201, rel_res.text
    release_data = rel_res.json()
    release_id = release_data["id"]

    assert release_data["status"] == "PENDING"
    assert release_data["fdr_id"] == fdr_id

    # Verify FDR status updated to RELEASE_REQUESTED
    fdr_check = client.get(f"/api/v1/fdr/{fdr_id}", headers=headers_inst).json()
    assert fdr_check["lifecycle_status"] == "RELEASE_REQUESTED"

    # 3. Authority authorizes release
    auth_decision_res = client.post(
        f"/api/v1/releases/{release_id}/authority-decision",
        json={
            "decision": "APPROVE_RELEASE",
            "remarks": "NOC verified, statutory tenure satisfied. Security deposit released to institution bank account."
        },
        headers=headers_auth
    )
    assert auth_decision_res.status_code == 200, auth_decision_res.text
    approved_rel = auth_decision_res.json()

    assert approved_rel["status"] == "APPROVED"
    assert approved_rel["authorization_reference"].startswith("AICTE/FIN/REL/")

    # Verify FDR status is now RELEASED
    fdr_final = client.get(f"/api/v1/fdr/{fdr_id}", headers=headers_inst).json()
    assert fdr_final["lifecycle_status"] == "RELEASED"
    assert approved_rel["authorization_reference"] in fdr_final["authority_remarks"]

# -------------------------------------------------------------------------
# Test 4: Authority Rejection of Release Petition
# -------------------------------------------------------------------------
def test_authority_rejection_of_release_petition():
    """Verify that when an Approving Authority rejects a release petition, the FDR returns to active/matured status."""
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    authority_token = get_auth_token("approving_auth@fdrsetu.gov.in")

    headers_inst = {"Authorization": f"Bearer {inst_token}"}
    headers_auth = {"Authorization": f"Bearer {authority_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-RELREJ-{uid}"

    res = client.post("/api/v1/fdr", json={
        "fdr_number": fdr_no,
        "bank_name": "Indian Bank",
        "branch_name": "Rohini",
        "ifsc_code": "IDIB0001234",
        "deposit_amount": "1000000.00",
        "issue_date": str(date.today() - timedelta(days=200)),
        "maturity_date": str(date.today() + timedelta(days=500)),
        "beneficiary": "Member Secretary, AICTE"
    }, headers=headers_inst)
    fdr_id = res.json()["id"]

    # Mark active in DB
    from app.core.database import SessionLocal
    from app.models.fdr import FDRRecord
    db = SessionLocal()
    f = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
    f.lifecycle_status = "APPROVED_ACTIVE"
    db.commit()
    db.close()

    # Request release
    rel_res = client.post(f"/api/v1/fdr/{fdr_id}/request-release", json={
        "release_reason": "Premature withdrawal requested",
        "refund_bank_name": "Indian Bank",
        "refund_account_number": "1122334455",
        "refund_ifsc": "IDIB0001234",
        "refund_beneficiary_name": "Delhi Institute of Technology"
    }, headers=headers_inst)
    release_id = rel_res.json()["id"]

    # Authority rejects release
    rej_rel_res = client.post(
        f"/api/v1/releases/{release_id}/authority-decision",
        json={
            "decision": "REJECT_RELEASE",
            "remarks": "Premature release denied: Mandatory 5-year lock-in period has not elapsed."
        },
        headers=headers_auth
    )
    assert rej_rel_res.status_code == 200
    assert rej_rel_res.json()["status"] == "REJECTED"

    # Verify FDR returned to APPROVED_ACTIVE
    fdr_check = client.get(f"/api/v1/fdr/{fdr_id}", headers=headers_inst).json()
    assert fdr_check["lifecycle_status"] == "APPROVED_ACTIVE"

# -------------------------------------------------------------------------
# Test 5: Release Blocked by Open Critical Discrepancy
# -------------------------------------------------------------------------
def test_release_blocked_by_open_critical_discrepancy():
    """Verify that an institution cannot initiate release if an unresolved critical discrepancy exists."""
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    officer_token = get_auth_token("scrutiny_officer@fdrsetu.gov.in")

    headers_inst = {"Authorization": f"Bearer {inst_token}"}
    headers_officer = {"Authorization": f"Bearer {officer_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-BLOCKED-{uid}"

    res = client.post("/api/v1/fdr", json={
        "fdr_number": fdr_no,
        "bank_name": "Bank of India",
        "branch_name": "Saket",
        "ifsc_code": "BKID0001234",
        "deposit_amount": "1500000.00",
        "issue_date": str(date.today() - timedelta(days=365)),
        "maturity_date": str(date.today() - timedelta(days=2)),
        "beneficiary": "Member Secretary, AICTE"
    }, headers=headers_inst)
    fdr_id = res.json()["id"]

    from app.core.database import SessionLocal
    from app.models.fdr import FDRRecord
    db = SessionLocal()
    f = db.query(FDRRecord).filter(FDRRecord.id == fdr_id).first()
    f.lifecycle_status = "APPROVED_ACTIVE"
    db.commit()
    db.close()

    # Officer raises a CRITICAL discrepancy
    client.post(
        f"/api/v1/fdr/{fdr_id}/discrepancies",
        json={
            "title": "Unresolved AICTE Regional Office Dispute",
            "description": "Lien confirmation revoked by bank pending court inquiry.",
            "severity": "CRITICAL"
        },
        headers=headers_officer
    )

    # Attempt to request release - MUST FAIL
    blocked_res = client.post(
        f"/api/v1/fdr/{fdr_id}/request-release",
        json={
            "release_reason": "Tenure completed",
            "refund_bank_name": "Bank of India",
            "refund_account_number": "1234567890",
            "refund_ifsc": "BKID0001234",
            "refund_beneficiary_name": "College Account"
        },
        headers=headers_inst
    )
    assert blocked_res.status_code == 400
    assert "unresolved compliance discrepancy" in blocked_res.json()["detail"].lower()

# -------------------------------------------------------------------------
# Test 6: Role Authorization and Tenant Isolation on Releases
# -------------------------------------------------------------------------
def test_role_authorization_and_tenant_isolation_on_releases():
    """Verify that only Approving Authority can record decisions and institutions cannot access foreign releases."""
    inst1_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    inst2_token = get_auth_token("inst2_admin@fdrsetu.gov.in")

    headers1 = {"Authorization": f"Bearer {inst1_token}"}
    headers2 = {"Authorization": f"Bearer {inst2_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-FORBID-{uid}"

    res = client.post("/api/v1/fdr", json={
        "fdr_number": fdr_no,
        "bank_name": "HDFC Bank",
        "branch_name": "Kailash Colony",
        "ifsc_code": "HDFC0001234",
        "deposit_amount": "2500000.00",
        "issue_date": str(date.today() - timedelta(days=100)),
        "maturity_date": str(date.today() + timedelta(days=265)),
        "beneficiary": "Member Secretary, AICTE"
    }, headers=headers1)
    fdr_id = res.json()["id"]

    # Institution 1 user attempts to make authority decision - MUST FAIL (403)
    auth_breach = client.post(
        f"/api/v1/fdr/{fdr_id}/authority-decision",
        json={"decision": "APPROVE_FDR", "remarks": "Self approval attempt"},
        headers=headers1
    )
    assert auth_breach.status_code == 403

    # Institution 2 attempts to request release on Institution 1's FDR - MUST FAIL (403)
    tenant_breach = client.post(
        f"/api/v1/fdr/{fdr_id}/request-release",
        json={
            "release_reason": "Cross-tenant release theft attempt",
            "refund_bank_name": "Hacked Bank",
            "refund_account_number": "999999",
            "refund_ifsc": "HDFC0001234",
            "refund_beneficiary_name": "Hacker"
        },
        headers=headers2
    )
    assert tenant_breach.status_code == 403

