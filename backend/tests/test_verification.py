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
# Test 1: Clean Pass on Valid Compliant FDR
# -------------------------------------------------------------------------
def test_verification_clean_pass():
    """Verify that a compliant FDR satisfies all 12 rules and receives a PASSED verdict."""
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-PASS-{uid}"

    # Create fully compliant FDR (3-year tenure, valid bank, valid amount, AICTE beneficiary)
    fdr_payload = {
        "fdr_number": fdr_no,
        "bank_name": "State Bank of India",
        "branch_name": "Parliament Street New Delhi",
        "ifsc_code": "SBIN0000691",
        "deposit_amount": "5000000.00",
        "issue_date": str(date.today() - timedelta(days=60)),
        "maturity_date": str(date.today() + timedelta(days=1035)),  # ~3 years
        "interest_rate": "7.10",
        "beneficiary": "Member Secretary, AICTE New Delhi"
    }
    create_res = client.post("/api/v1/fdr", json=fdr_payload, headers=headers)
    assert create_res.status_code == 201, create_res.text
    fdr_id = create_res.json()["id"]

    # Upload Primary Instrument Document
    files = {"file": (f"{fdr_no}.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
    upload_res = client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        data={"document_type": "PRIMARY_INSTRUMENT"},
        files=files,
        headers=headers
    )
    assert upload_res.status_code == 201, upload_res.text

    # Run Verification
    verify_res = client.post(f"/api/v1/fdr/{fdr_id}/verify", headers=headers)
    assert verify_res.status_code == 200, verify_res.text
    report = verify_res.json()

    assert report["fdr_id"] == fdr_id
    assert report["overall_status"] == "PASSED"
    assert report["failed_count"] == 0
    assert report["total_rules_evaluated"] == 12
    assert report["passed_count"] >= 11

    # Verify FDR record status synchronized
    fdr_check = client.get(f"/api/v1/fdr/{fdr_id}", headers=headers).json()
    assert fdr_check["verification_status"] == "VERIFIED"

    # Verify report retrieval endpoint
    get_report_res = client.get(f"/api/v1/fdr/{fdr_id}/verification-report", headers=headers)
    assert get_report_res.status_code == 200
    assert get_report_res.json()["id"] == report["id"]

# -------------------------------------------------------------------------
# Test 2: Tenure, Amount, and Beneficiary Discrepancies
# -------------------------------------------------------------------------
def test_verification_detects_tenure_and_amount_discrepancies():
    """Verify that tenure under 12 months, amount below ₹ 1,00,000, and non-AICTE beneficiary are detected and flagged."""
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-DEFECT-{uid}"

    # Invalid FDR: 3 months duration, ₹ 20,000 amount, Private beneficiary
    fdr_payload = {
        "fdr_number": fdr_no,
        "bank_name": "Canara Bank",
        "branch_name": "Rohini Branch",
        "ifsc_code": "CNRB0001234",
        "deposit_amount": "20000.00",  # Below 1,00,000
        "issue_date": str(date.today() - timedelta(days=10)),
        "maturity_date": str(date.today() + timedelta(days=80)),  # 90 days (~3 months)
        "interest_rate": "5.50",
        "beneficiary": "Self Account Holder (Private)"  # Missing AICTE
    }
    create_res = client.post("/api/v1/fdr", json=fdr_payload, headers=headers)
    fdr_id = create_res.json()["id"]

    # Upload document
    client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        data={"document_type": "PRIMARY_INSTRUMENT"},
        files={"file": (f"{fdr_no}.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
        headers=headers
    )

    # Run Verification
    verify_res = client.post(f"/api/v1/fdr/{fdr_id}/verify", headers=headers)
    assert verify_res.status_code == 200
    report = verify_res.json()

    assert report["overall_status"] == "FAILED_DISCREPANCIES"
    assert report["failed_count"] >= 3

    # Check generated discrepancies
    disc_res = client.get(f"/api/v1/fdr/{fdr_id}/discrepancies", headers=headers)
    assert disc_res.status_code == 200
    discs = disc_res.json()
    rule_codes = [d["rule_code"] for d in discs]

    assert "RULE_MATURITY_TENURE" in rule_codes
    assert "RULE_AMOUNT_CONSISTENCY" in rule_codes
    assert "RULE_BENEFICIARY_MATCH" in rule_codes

    # Check FDR status updated to DISCREPANCY_FLAGGED
    fdr_check = client.get(f"/api/v1/fdr/{fdr_id}", headers=headers).json()
    assert fdr_check["verification_status"] == "DISCREPANCY_FLAGGED"

# -------------------------------------------------------------------------
# Test 3: Duplicate Detection and Missing Document Prevention
# -------------------------------------------------------------------------
def test_verification_detects_duplicate_and_missing_document():
    """Verify system-wide duplicate FDR detection and missing primary instrument checks."""
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    uid = uuid.uuid4().hex[:6].upper()
    common_fdr_no = f"FDR-DUPCHK-{uid}"

    # 1. Create first FDR and attach document
    fdr1_res = client.post("/api/v1/fdr", json={
        "fdr_number": common_fdr_no,
        "bank_name": "Punjab National Bank",
        "branch_name": "Karol Bagh",
        "ifsc_code": "PUNB0001234",
        "deposit_amount": "1500000.00",
        "issue_date": str(date.today() - timedelta(days=20)),
        "maturity_date": str(date.today() + timedelta(days=400)),
        "beneficiary": "Member Secretary, AICTE"
    }, headers=headers)
    fdr1_id = fdr1_res.json()["id"]

    client.post(
        f"/api/v1/fdr/{fdr1_id}/documents",
        data={"document_type": "PRIMARY_INSTRUMENT"},
        files={"file": (f"{common_fdr_no}.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
        headers=headers
    )

    # 2. Create second FDR without documents and with the same FDR number (different branch/case)
    fdr_no_second = f"FDR-NODOC-{uid}"
    fdr2_res = client.post("/api/v1/fdr", json={
        "fdr_number": fdr_no_second,
        "bank_name": "Punjab National Bank",
        "branch_name": "Lajpat Nagar",
        "ifsc_code": "PUNB0001234",
        "deposit_amount": "2000000.00",
        "issue_date": str(date.today() - timedelta(days=10)),
        "maturity_date": str(date.today() + timedelta(days=500)),
        "beneficiary": "Member Secretary, AICTE"
    }, headers=headers)
    fdr2_id = fdr2_res.json()["id"]

    # Run verification on FDR2 without documents
    verify2 = client.post(f"/api/v1/fdr/{fdr2_id}/verify", headers=headers).json()
    rule_results = {r["rule_code"]: r for r in verify2["rule_results"]}
    assert rule_results["RULE_MISSING_DOCUMENT"]["status"] == "FAILED"

# -------------------------------------------------------------------------
# Test 4: Discrepancy Lifecycle & Scrutiny Recommendation
# -------------------------------------------------------------------------
def test_discrepancy_lifecycle_and_scrutiny_recommendation():
    """Verify full discrepancy lifecycle: Institution responds -> Scrutiny Officer resolves -> Officer recommends decision."""
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    officer_token = get_auth_token("scrutiny_officer@fdrsetu.gov.in")

    headers_inst = {"Authorization": f"Bearer {inst_token}"}
    headers_officer = {"Authorization": f"Bearer {officer_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-SCRUTINY-{uid}"

    # Create FDR and upload doc
    fdr_res = client.post("/api/v1/fdr", json={
        "fdr_number": fdr_no,
        "bank_name": "State Bank of India",
        "branch_name": "IIT Hauz Khas",
        "ifsc_code": "SBIN0001077",
        "deposit_amount": "3000000.00",
        "issue_date": str(date.today() - timedelta(days=30)),
        "maturity_date": str(date.today() + timedelta(days=1000)),
        "beneficiary": "Member Secretary, AICTE"
    }, headers=headers_inst)
    fdr_id = fdr_res.json()["id"]

    client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        data={"document_type": "PRIMARY_INSTRUMENT"},
        files={"file": (f"{fdr_no}.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
        headers=headers_inst
    )

    # Scrutiny Officer raises manual observation
    raise_res = client.post(
        f"/api/v1/fdr/{fdr_id}/discrepancies",
        json={
            "title": "Bank Branch Seal Partially Obscured",
            "description": "The official branch stamp on page 1 is faintly printed. Please provide a bank certificate confirming lien.",
            "severity": "HIGH",
            "rule_code": "SCRUTINY_OFFICER_OBSERVATION"
        },
        headers=headers_officer
    )
    assert raise_res.status_code == 201, raise_res.text
    disc_id = raise_res.json()["id"]
    assert raise_res.json()["status"] == "OPEN"

    # Institution Admin responds with explanation
    resp_res = client.post(
        f"/api/v1/discrepancies/{disc_id}/respond",
        json={"response_text": "We have attached the official bank branch confirmation letter under Supporting Documents."},
        headers=headers_inst
    )
    assert resp_res.status_code == 200, resp_res.text
    assert resp_res.json()["institution_response"] == "We have attached the official bank branch confirmation letter under Supporting Documents."

    # Scrutiny Officer resolves the discrepancy
    resolve_res = client.post(
        f"/api/v1/discrepancies/{disc_id}/resolve",
        json={"resolution_note": "Bank confirmation letter examined and found authentic. Discrepancy closed.", "status": "RESOLVED"},
        headers=headers_officer
    )
    assert resolve_res.status_code == 200, resolve_res.text
    assert resolve_res.json()["status"] == "RESOLVED"
    assert "Discrepancy closed" in resolve_res.json()["officer_resolution_note"]

    # Scrutiny Officer records recommendation
    rec_res = client.post(
        f"/api/v1/fdr/{fdr_id}/scrutiny-recommendation",
        json={
            "recommendation": "RECOMMEND_APPROVAL",
            "remarks": "All documents cryptographically verified, AI OCR reconciled, and bank confirmation validated. Recommended for Approving Authority sign-off."
        },
        headers=headers_officer
    )
    assert rec_res.status_code == 200, rec_res.text
    assert "RECOMMEND_APPROVAL" in rec_res.json()["scrutiny_remarks"]

# -------------------------------------------------------------------------
# Test 5: Administrator Rule Configuration
# -------------------------------------------------------------------------
def test_admin_rule_configuration():
    """Verify that System Administrators can configure verification rules and non-admins are restricted."""
    admin_token = get_auth_token("sys_admin@fdrsetu.gov.in")
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")

    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_inst = {"Authorization": f"Bearer {inst_token}"}

    # List all 12 rules
    rules_res = client.get("/api/v1/verification/rules", headers=headers_admin)
    assert rules_res.status_code == 200, rules_res.text
    rules = rules_res.json()
    assert len(rules) >= 12

    target_rule = rules[0]
    rule_id = target_rule["id"]

    # Admin configures rule (updates parameters or toggles)
    patch_res = client.patch(
        f"/api/v1/verification/rules/{rule_id}",
        json={"severity": "CRITICAL", "parameters": {"min_tenure_months": 24}},
        headers=headers_admin
    )
    assert patch_res.status_code == 200, patch_res.text
    assert patch_res.json()["severity"] == "CRITICAL"
    assert patch_res.json()["parameters"]["min_tenure_months"] == 24

    # Institution Admin is forbidden from configuring rules
    forbidden_res = client.patch(
        f"/api/v1/verification/rules/{rule_id}",
        json={"is_enabled": False},
        headers=headers_inst
    )
    assert forbidden_res.status_code == 403
