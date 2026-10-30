import io
import uuid
from decimal import Decimal
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.seed import init_db
from app.lifecycle.service import LifecycleService

init_db()
client = TestClient(app)

def get_auth_token(email: str, password: str = "Admin@123") -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": password}
    )
    assert res.status_code == 200, f"Authentication failed for {email}: {res.text}"
    return res.json()["access_token"]

# -------------------------------------------------------------------------
# Test 1: Dynamic Days-to-Maturity Calculation & Milestone Bucketing
# -------------------------------------------------------------------------
def test_maturity_calculation_milestones():
    """Verify programmatic milestone categorization and urgency flags across date intervals."""
    today = date.today()

    # 1. Healthy active (> 90 days)
    res_healthy = LifecycleService.calculate_maturity_status(today + timedelta(days=200))
    assert res_healthy["milestone"] == "HEALTHY_ACTIVE"
    assert res_healthy["is_renewal_due"] is False
    assert res_healthy["is_matured"] is False

    # 2. Within 90 days (61 - 90 days)
    res_90 = LifecycleService.calculate_maturity_status(today + timedelta(days=75))
    assert res_90["milestone"] == "WITHIN_90_DAYS"
    assert res_90["is_renewal_due"] is True
    assert res_90["is_matured"] is False

    # 3. Within 30 days
    res_30 = LifecycleService.calculate_maturity_status(today + timedelta(days=25))
    assert res_30["milestone"] == "WITHIN_30_DAYS"
    assert res_30["is_renewal_due"] is True

    # 4. Critical: within 7 days
    res_7 = LifecycleService.calculate_maturity_status(today + timedelta(days=4))
    assert res_7["milestone"] == "WITHIN_7_DAYS"
    assert res_7["urgency"] == "HIGH"

    # 5. Matures today (0 days)
    res_today = LifecycleService.calculate_maturity_status(today)
    assert res_today["milestone"] == "MATURES_TODAY"
    assert res_today["is_matured"] is True

    # 6. Overdue / Past maturity (< 0 days)
    res_overdue = LifecycleService.calculate_maturity_status(today - timedelta(days=15))
    assert res_overdue["milestone"] == "OVERDUE_MATURED"
    assert res_overdue["is_matured"] is True
    assert res_overdue["urgency"] == "CRITICAL"

# -------------------------------------------------------------------------
# Test 2: Automated Maturity Scan and Status Transitions
# -------------------------------------------------------------------------
def test_automated_maturity_scan_transitions():
    """Verify that scanning maturities automatically transitions instruments to RENEWAL_DUE or MATURED."""
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    officer_token = get_auth_token("scrutiny_officer@fdrsetu.gov.in")

    headers_inst = {"Authorization": f"Bearer {inst_token}"}
    headers_officer = {"Authorization": f"Bearer {officer_token}"}

    uid = uuid.uuid4().hex[:6].upper()

    # 1. Create FDR maturing in 40 days (should become RENEWAL_DUE)
    fdr1_payload = {
        "fdr_number": f"FDR-DUE-{uid}",
        "bank_name": "State Bank of India",
        "branch_name": "Chandni Chowk",
        "ifsc_code": "SBIN0000691",
        "deposit_amount": "2500000.00",
        "issue_date": str(date.today() - timedelta(days=365)),
        "maturity_date": str(date.today() + timedelta(days=40)),  # <= 90 days
        "beneficiary": "Member Secretary, AICTE"
    }
    res1 = client.post("/api/v1/fdr", json=fdr1_payload, headers=headers_inst)
    fdr1_id = res1.json()["id"]

    # 2. Create FDR already expired 5 days ago (should become MATURED)
    fdr2_payload = {
        "fdr_number": f"FDR-EXP-{uid}",
        "bank_name": "Bank of Baroda",
        "branch_name": "Connaught Place",
        "ifsc_code": "BARB0000001",
        "deposit_amount": "3000000.00",
        "issue_date": str(date.today() - timedelta(days=730)),
        "maturity_date": str(date.today() - timedelta(days=5)),  # Expired
        "beneficiary": "Member Secretary, AICTE"
    }
    res2 = client.post("/api/v1/fdr", json=fdr2_payload, headers=headers_inst)
    fdr2_id = res2.json()["id"]

    # Manually promote both to APPROVED_ACTIVE in DB to simulate active portfolio
    from app.core.database import SessionLocal
    from app.models.fdr import FDRRecord
    db = SessionLocal()
    f1 = db.query(FDRRecord).filter(FDRRecord.id == fdr1_id).first()
    f2 = db.query(FDRRecord).filter(FDRRecord.id == fdr2_id).first()
    f1.lifecycle_status = "APPROVED_ACTIVE"
    f2.lifecycle_status = "APPROVED_ACTIVE"
    db.commit()
    db.close()

    # Trigger Maturity Scan via API
    scan_res = client.post("/api/v1/lifecycle/scan-maturities", headers=headers_officer)
    assert scan_res.status_code == 200, scan_res.text
    scan_data = scan_res.json()

    assert scan_data["status"] == "success"
    assert scan_data["total_scanned"] >= 2
    assert scan_data["matured_count"] >= 1
    assert scan_data["renewal_due_count"] >= 1

    # Verify FDR1 transitioned to RENEWAL_DUE
    check_fdr1 = client.get(f"/api/v1/fdr/{fdr1_id}", headers=headers_inst).json()
    assert check_fdr1["lifecycle_status"] == "RENEWAL_DUE"

    # Verify FDR2 transitioned to MATURED
    check_fdr2 = client.get(f"/api/v1/fdr/{fdr2_id}", headers=headers_inst).json()
    assert check_fdr2["lifecycle_status"] == "MATURED"

# -------------------------------------------------------------------------
# Test 3: Renewal Initiation and Bidirectional Lineage Chaining
# -------------------------------------------------------------------------
def test_initiate_renewal_workflow_and_chaining():
    """Verify renewal creation: original becomes RENEWAL_SUBMITTED, renewed gets previous_fdr_id, lineage traces chain."""
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {inst_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    orig_fdr_no = f"FDR-ORIG-{uid}"
    rnw_fdr_no = f"FDR-RNW-{uid}"

    # 1. Create original FDR and mark as APPROVED_ACTIVE
    fdr_payload = {
        "fdr_number": orig_fdr_no,
        "bank_name": "Canara Bank",
        "branch_name": "Mayur Vihar",
        "ifsc_code": "CNRB0001234",
        "deposit_amount": "4000000.00",
        "issue_date": str(date.today() - timedelta(days=1095)),
        "maturity_date": str(date.today() + timedelta(days=20)),
        "beneficiary": "Member Secretary, AICTE"
    }
    create_res = client.post("/api/v1/fdr", json=fdr_payload, headers=headers)
    orig_fdr_id = create_res.json()["id"]

    # 2. Initiate Renewal linked to original
    renewal_payload = {
        "fdr_number": rnw_fdr_no,
        "bank_name": "Canara Bank",
        "branch_name": "Mayur Vihar",
        "ifsc_code": "CNRB0001234",
        "deposit_amount": "4000000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=1095)),  # +3 years
        "interest_rate": "7.25",
        "beneficiary": "Member Secretary, AICTE"
    }
    renew_res = client.post(f"/api/v1/fdr/{orig_fdr_id}/renew", json=renewal_payload, headers=headers)
    assert renew_res.status_code == 201, renew_res.text
    renewed_fdr = renew_res.json()

    assert renewed_fdr["fdr_number"] == rnw_fdr_no
    assert renewed_fdr["previous_fdr_id"] == orig_fdr_id
    assert renewed_fdr["lifecycle_status"] == "DRAFT"

    # Verify original FDR is transitioned to RENEWAL_SUBMITTED
    orig_check = client.get(f"/api/v1/fdr/{orig_fdr_id}", headers=headers).json()
    assert orig_check["lifecycle_status"] == "RENEWAL_SUBMITTED"

    # 3. Retrieve Renewal Lineage from either node in the chain
    lineage_res = client.get(f"/api/v1/fdr/{renewed_fdr['id']}/renewal-history", headers=headers)
    assert lineage_res.status_code == 200, lineage_res.text
    chain = lineage_res.json()

    assert len(chain) == 2
    assert chain[0]["fdr_number"] == orig_fdr_no
    assert chain[1]["fdr_number"] == rnw_fdr_no
    assert chain[1]["is_current"] is True

# -------------------------------------------------------------------------
# Test 4: Maturity Timeline Analytics
# -------------------------------------------------------------------------
def test_maturity_timeline_endpoint():
    """Verify aggregated calendar maturity timeline metrics across buckets."""
    officer_token = get_auth_token("scrutiny_officer@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {officer_token}"}

    timeline_res = client.get("/api/v1/lifecycle/maturity-timeline", headers=headers)
    assert timeline_res.status_code == 200, timeline_res.text
    data = timeline_res.json()

    assert "total_instruments" in data
    assert "total_statutory_value" in data
    assert "buckets" in data
    assert "counts" in data

    buckets = data["buckets"]
    assert "OVERDUE_MATURED" in buckets
    assert "WITHIN_7_DAYS" in buckets
    assert "WITHIN_30_DAYS" in buckets
    assert "WITHIN_90_DAYS" in buckets
    assert "HEALTHY_ACTIVE" in buckets

# -------------------------------------------------------------------------
# Test 5: Tenant Isolation on Renewals
# -------------------------------------------------------------------------
def test_tenant_isolation_on_renewals():
    """Verify that an Institution Admin cannot initiate a renewal on another institution's FDR."""
    inst1_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    inst2_token = get_auth_token("inst2_admin@fdrsetu.gov.in")

    headers1 = {"Authorization": f"Bearer {inst1_token}"}
    headers2 = {"Authorization": f"Bearer {inst2_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-ISOL-{uid}"

    # Institution 1 creates FDR
    create_res = client.post("/api/v1/fdr", json={
        "fdr_number": fdr_no,
        "bank_name": "Indian Bank",
        "branch_name": "Rohini",
        "ifsc_code": "IDIB0001234",
        "deposit_amount": "2000000.00",
        "issue_date": str(date.today() - timedelta(days=100)),
        "maturity_date": str(date.today() + timedelta(days=265)),
        "beneficiary": "Member Secretary, AICTE"
    }, headers=headers1)
    fdr1_id = create_res.json()["id"]

    # Institution 2 attempts to renew Institution 1's FDR
    forbidden_renew = client.post(f"/api/v1/fdr/{fdr1_id}/renew", json={
        "fdr_number": f"FDR-HIJACK-{uid}",
        "bank_name": "Indian Bank",
        "branch_name": "Rohini",
        "ifsc_code": "IDIB0001234",
        "deposit_amount": "2000000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=365)),
        "beneficiary": "Member Secretary, AICTE"
    }, headers=headers2)
    assert forbidden_renew.status_code == 403

    # Institution 2 attempts to view renewal history
    forbidden_history = client.get(f"/api/v1/fdr/{fdr1_id}/renewal-history", headers=headers2)
    assert forbidden_history.status_code == 403
