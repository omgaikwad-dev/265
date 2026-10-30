import pytest
import time
import uuid
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.core.seed import init_db

# Ensure all tables and seed data are initialized
init_db()

client = TestClient(app)

def get_auth_token(email: str = "sys_admin@fdrsetu.gov.in", password: str = "Admin@123") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": password}
    )
    assert response.status_code == 200, f"Login failed for {email}: {response.text}"
    return response.json()["access_token"]

def test_notification_feed_and_read_actions():
    """
    Verifies notification fetching, single read marker, and bulk mark-all-read.
    """
    token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch initial notifications
    res = client.get("/api/v1/notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "unread_count" in data
    assert "total_count" in data
    assert isinstance(data["items"], list)

    # 2. Dispatch simulated notification via admin
    admin_token = get_auth_token("sys_admin@fdrsetu.gov.in")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    dispatch_res = client.post(
        "/api/v1/notifications/test-dispatch",
        headers=admin_headers,
        json={
            "title": "Automated Scrutiny Compliance Notice",
            "message": "Please review discrepancy observations for your active FDRs.",
            "category": "SCRUTINY",
            "severity": "WARNING",
            "recipient_role": "ROLE_INSTITUTION_ADMIN",
            "institution_id": 1,
            "channel": "IN_APP",
            "action_link": "/fdrs"
        }
    )
    assert dispatch_res.status_code == 200
    notif_id = dispatch_res.json()["id"]

    # 3. Institution admin fetches notifications again
    res2 = client.get("/api/v1/notifications", headers=headers)
    assert res2.status_code == 200
    items2 = res2.json()["items"]
    found = [n for n in items2 if n["id"] == notif_id]
    assert len(found) == 1
    assert found[0]["is_read"] is False

    # 4. Mark single notification as read
    patch_res = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["is_read"] is True
    assert patch_res.json()["read_at"] is not None

    # 5. Bulk mark all read
    bulk_res = client.post("/api/v1/notifications/mark-all-read", headers=headers)
    assert bulk_res.status_code == 200
    assert "marked_count" in bulk_res.json()

    # Verify unread count is 0
    res3 = client.get("/api/v1/notifications?unread_only=true", headers=headers)
    assert res3.status_code == 200
    assert res3.json()["unread_count"] == 0

def test_notification_tenant_isolation():
    """
    Ensures Institution 2 cannot read or tamper with Institution 1 notifications.
    """
    admin_token = get_auth_token("sys_admin@fdrsetu.gov.in")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Dispatch notification strictly for Institution 1
    dispatch_res = client.post(
        "/api/v1/notifications/test-dispatch",
        headers=admin_headers,
        json={
            "title": "Private Tenant Notice Inst 1",
            "message": "Confidential deposit notice for Institution 1 only.",
            "category": "SYSTEM",
            "severity": "HIGH",
            "recipient_role": "ROLE_INSTITUTION_ADMIN",
            "institution_id": 1,
            "channel": "IN_APP"
        }
    )
    assert dispatch_res.status_code == 200
    notif_id = dispatch_res.json()["id"]

    # Institution 2 accesses notifications
    inst2_token = get_auth_token("inst2_admin@fdrsetu.gov.in")
    inst2_headers = {"Authorization": f"Bearer {inst2_token}"}

    feed_res = client.get("/api/v1/notifications", headers=inst2_headers)
    assert feed_res.status_code == 200
    inst2_items = feed_res.json()["items"]
    # Institution 1 notification must NOT appear in Inst 2 feed
    assert not any(n["id"] == notif_id for n in inst2_items)

    # Institution 2 attempts to mark Inst 1's notification as read -> must be 403 Forbidden
    tamper_res = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=inst2_headers)
    assert tamper_res.status_code == 403

def test_milestone_and_multitier_escalation_engine():
    """
    Tests automated maturity milestone alerts and Tier 1, Tier 2, and Tier 3 escalations.
    """
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    inst_headers = {"Authorization": f"Bearer {inst_token}"}

    today = date.today()

    suffix = str(uuid.uuid4())[:8]

    # Create FDR overdue by 8 days (Tier 1: 7-14 days overdue)
    fdr_tier1_res = client.post(
        "/api/v1/fdr",
        headers=inst_headers,
        json={
            "fdr_number": f"TEST-NOTIF-T1-{suffix}",
            "bank_name": "State Bank of India",
            "branch_name": "Main Branch",
            "ifsc_code": "SBIN0001234",
            "deposit_amount": 2000000.0,
            "issue_date": (today - timedelta(days=400)).isoformat(),
            "maturity_date": (today - timedelta(days=8)).isoformat(),
            "beneficiary": "Member Secretary, AICTE"
        }
    )
    assert fdr_tier1_res.status_code == 201, f"Failed to create draft 1: {fdr_tier1_res.text}"
    fdr1_id = fdr_tier1_res.json()["id"]

    # Create FDR overdue by 18 days (Tier 2: 15-29 days overdue)
    fdr_tier2_res = client.post(
        "/api/v1/fdr",
        headers=inst_headers,
        json={
            "fdr_number": f"TEST-NOTIF-T2-{suffix}",
            "bank_name": "Punjab National Bank",
            "branch_name": "Circle Branch",
            "ifsc_code": "PUNB0011223",
            "deposit_amount": 3000000.0,
            "issue_date": (today - timedelta(days=400)).isoformat(),
            "maturity_date": (today - timedelta(days=18)).isoformat(),
            "beneficiary": "Member Secretary, AICTE"
        }
    )
    assert fdr_tier2_res.status_code == 201, f"Failed to create draft 2: {fdr_tier2_res.text}"
    fdr2_id = fdr_tier2_res.json()["id"]

    # Create FDR overdue by 35 days (Tier 3: 30+ days overdue)
    fdr_tier3_res = client.post(
        "/api/v1/fdr",
        headers=inst_headers,
        json={
            "fdr_number": f"TEST-NOTIF-T3-{suffix}",
            "bank_name": "Bank of Baroda",
            "branch_name": "City Branch",
            "ifsc_code": "BARB0001234",
            "deposit_amount": 4000000.0,
            "issue_date": (today - timedelta(days=400)).isoformat(),
            "maturity_date": (today - timedelta(days=35)).isoformat(),
            "beneficiary": "Member Secretary, AICTE"
        }
    )
    assert fdr_tier3_res.status_code == 201, f"Failed to create draft 3: {fdr_tier3_res.text}"
    fdr3_id = fdr_tier3_res.json()["id"]

    # Set them to APPROVED_ACTIVE so escalation engine considers them
    from app.core.database import SessionLocal
    from app.models.fdr import FDRRecord
    db = SessionLocal()
    try:
        for fid in [fdr1_id, fdr2_id, fdr3_id]:
            rec = db.query(FDRRecord).filter(FDRRecord.id == fid).first()
            if rec:
                rec.lifecycle_status = "APPROVED_ACTIVE"
        db.commit()
    finally:
        db.close()

    # Trigger escalation engine via Approving Authority
    auth_token = get_auth_token("approving_auth@fdrsetu.gov.in")
    auth_headers = {"Authorization": f"Bearer {auth_token}"}

    scan_res = client.post("/api/v1/notifications/trigger-escalation", headers=auth_headers)
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    assert scan_data["scanned_fdrs"] >= 3
    assert scan_data["escalations_triggered"] >= 3
    assert scan_data["notifications_dispatched"] >= 6

    # Verify Approving Authority received Tier 3 escalation
    auth_notifs = client.get("/api/v1/notifications?category=ESCALATION", headers=auth_headers).json()["items"]
    assert any("TIER 3" in n["title"] and n["fdr_id"] == fdr3_id for n in auth_notifs)

    # Verify Scrutiny Officer received Tier 2 and Tier 3 notifications
    so_token = get_auth_token("scrutiny_officer@fdrsetu.gov.in")
    so_headers = {"Authorization": f"Bearer {so_token}"}
    so_notifs = client.get("/api/v1/notifications?category=ESCALATION", headers=so_headers).json()["items"]
    assert any("TIER 2" in n["title"] and n["fdr_id"] == fdr2_id for n in so_notifs)
    assert any("TIER 3" in n["title"] and n["fdr_id"] == fdr3_id for n in so_notifs)

    # Verify Institution Admin received notifications
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    inst_headers = {"Authorization": f"Bearer {inst_token}"}
    inst_notifs = client.get("/api/v1/notifications?category=ESCALATION", headers=inst_headers).json()["items"]
    assert any("TIER 1" in n["title"] and n["fdr_id"] == fdr1_id for n in inst_notifs)

def test_role_authorization_on_trigger_escalation():
    """
    Ensures only authorized administrative roles can trigger the manual escalation scan.
    """
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    inst_headers = {"Authorization": f"Bearer {inst_token}"}

    res = client.post("/api/v1/notifications/trigger-escalation", headers=inst_headers)
    assert res.status_code == 403

def test_escalation_history_endpoint():
    """
    Verifies that escalation logs can be queried via REST API.
    """
    token = get_auth_token("scrutiny_officer@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/notifications/escalation-logs", headers=headers)
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert "escalation_level" in logs[0]
    assert "reason" in logs[0]
    assert "recipients_notified" in logs[0]
