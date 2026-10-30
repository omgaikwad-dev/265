import io
import uuid
from decimal import Decimal
from datetime import date, timedelta
import pytest
import pymupdf
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

def generate_fdr_pdf(
    fdr_number: str = "FDR-AICTE-998877",
    bank_name: str = "STATE BANK OF INDIA",
    branch: str = "Indraprastha Estate Branch, New Delhi",
    ifsc: str = "SBIN0001234",
    amount: str = "Rs. 5,00,000.00",
    issue_date: str = "15/01/2024",
    maturity_date: str = "15/01/2029",
    rate: str = "7.25% p.a.",
    beneficiary: str = "Member Secretary, AICTE New Delhi"
) -> bytes:
    """Generate a clean synthetic Fixed Deposit Receipt PDF for OCR validation."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842) # Standard A4

    page.insert_text(pymupdf.Point(50, 60), bank_name, fontsize=16)
    page.insert_text(pymupdf.Point(50, 90), "TERM / FIXED DEPOSIT RECEIPT (FDR)", fontsize=13)
    page.insert_text(pymupdf.Point(50, 130), f"FDR Certificate No: {fdr_number}", fontsize=11)
    page.insert_text(pymupdf.Point(50, 160), f"Branch Name: {branch}", fontsize=11)
    page.insert_text(pymupdf.Point(50, 190), f"Branch IFSC Code: {ifsc}", fontsize=11)
    page.insert_text(pymupdf.Point(50, 220), f"Principal Deposit Sum: {amount}", fontsize=11)
    page.insert_text(pymupdf.Point(50, 250), f"Date of Issue / Deposit: {issue_date}", fontsize=11)
    page.insert_text(pymupdf.Point(50, 280), f"Date of Maturity: {maturity_date}", fontsize=11)
    page.insert_text(pymupdf.Point(50, 310), f"Contracted Interest Rate: {rate}", fontsize=11)
    page.insert_text(pymupdf.Point(50, 340), f"Beneficiary / In Favour Of: {beneficiary}", fontsize=11)
    page.insert_text(pymupdf.Point(50, 380), "Authorized Bank Signatory & Seal", fontsize=10)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_ocr_extract_end_to_end():
    """Verify AI OCR extraction pipeline: Document upload -> Text extraction -> Field parsing -> Confidence scoring."""
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {inst_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    expected_fdr_no = f"FDR-AICTE-{uid}"
    expected_ifsc = "SBIN0001234"
    expected_bank = "State Bank of India"

    # 1. Create a draft FDR
    fdr_payload = {
        "fdr_number": expected_fdr_no,
        "bank_name": expected_bank,
        "branch_name": "Indraprastha Estate",
        "ifsc_code": expected_ifsc,
        "deposit_amount": "500000.00",
        "issue_date": "2024-01-15",
        "maturity_date": "2029-01-15",
        "interest_rate": "7.25",
        "beneficiary": "Member Secretary, AICTE"
    }
    res = client.post("/api/v1/fdr", json=fdr_payload, headers=headers)
    assert res.status_code == 201, res.text
    fdr_id = res.json()["id"]

    # 2. Upload synthetic FDR PDF
    pdf_bytes = generate_fdr_pdf(
        fdr_number=expected_fdr_no,
        bank_name="STATE BANK OF INDIA",
        branch="Indraprastha Estate Branch, New Delhi",
        ifsc=expected_ifsc,
        amount="Rs. 5,00,000.00",
        issue_date="15/01/2024",
        maturity_date="15/01/2029",
        rate="7.25%",
        beneficiary="Member Secretary, AICTE New Delhi"
    )

    files = {"file": (f"{expected_fdr_no}.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        data={"document_type": "PRIMARY_INSTRUMENT"},
        files=files,
        headers=headers
    )
    assert upload_res.status_code == 201, upload_res.text

    # 3. Trigger AI OCR Extraction
    extract_res = client.post(f"/api/v1/fdr/{fdr_id}/extract", headers=headers)
    assert extract_res.status_code == 200, extract_res.text
    data = extract_res.json()

    # 4. Verify OCR structured output and confidence scoring
    assert data["fdr_id"] == fdr_id
    assert "raw_text" in data and len(data["raw_text"]) > 50
    assert "PyMuPDF" in data["processing_engine"] or "Tesseract" in data["processing_engine"]
    assert data["overall_confidence"] >= 80.0
    assert data["processing_time_ms"] > 0

    fields = data["extracted_fields"]
    confidences = data["field_confidences"]

    # Check extracted values
    assert expected_fdr_no in fields["fdr_number"]
    assert "STATE BANK OF INDIA" in fields["bank_name"].upper()
    assert fields["ifsc_code"] == expected_ifsc
    assert Decimal(str(fields["deposit_amount"])) == Decimal("500000")
    assert fields["issue_date"] == "2024-01-15"
    assert fields["maturity_date"] == "2029-01-15"
    assert "AICTE" in fields["beneficiary"]

    # Check field confidence scores
    for field_name in ["fdr_number", "bank_name", "ifsc_code", "deposit_amount", "issue_date", "maturity_date"]:
        assert field_name in confidences
        assert confidences[field_name] >= 75.0, f"Low confidence for {field_name}: {confidences[field_name]}"

    # Verify FDR status updated to COMPLETED
    fdr_check = client.get(f"/api/v1/fdr/{fdr_id}", headers=headers).json()
    assert fdr_check["ocr_status"] in ["COMPLETED", "OCR_COMPLETED"]

def test_ocr_get_and_correct_workflow():
    """Verify human-in-the-loop review: Fetching extraction and applying human corrections."""
    inst_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    headers = {"Authorization": f"Bearer {inst_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-CORR-{uid}"

    # Create FDR & upload
    fdr_payload = {
        "fdr_number": fdr_no,
        "bank_name": "Punjab National Bank",
        "branch_name": "Connaught Place",
        "ifsc_code": "PUNB0001234",
        "deposit_amount": "1000000.00",
        "issue_date": "2024-02-01",
        "maturity_date": "2027-02-01"
    }
    res = client.post("/api/v1/fdr", json=fdr_payload, headers=headers)
    fdr_id = res.json()["id"]

    pdf_bytes = generate_fdr_pdf(fdr_number=fdr_no, bank_name="PUNJAB NATIONAL BANK", ifsc="PUNB0001234")
    client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        data={"document_type": "PRIMARY_INSTRUMENT"},
        files={"file": (f"{fdr_no}.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers
    )

    # Extract
    client.post(f"/api/v1/fdr/{fdr_id}/extract", headers=headers)

    # Fetch stored extraction
    get_res = client.get(f"/api/v1/fdr/{fdr_id}/extraction", headers=headers)
    assert get_res.status_code == 200
    ext_data = get_res.json()
    assert ext_data["fdr_id"] == fdr_id

    # Apply correction (e.g., human reviewer edits branch name and interest rate)
    correction_payload = {
        "fdr_number": fdr_no,
        "bank_name": "Punjab National Bank",
        "branch_name": "Connaught Place Specialized Branch",
        "ifsc_code": "PUNB0001234",
        "deposit_amount": "1000000.00",
        "issue_date": "2024-02-01",
        "maturity_date": "2027-02-01",
        "interest_rate": "7.50",
        "beneficiary": "Member Secretary, AICTE New Delhi"
    }
    patch_res = client.patch(
        f"/api/v1/fdr/{fdr_id}/extraction",
        json={"corrected_fields": correction_payload},
        headers=headers
    )
    assert patch_res.status_code == 200
    updated_fdr = patch_res.json()
    assert updated_fdr["ocr_status"] == "OCR_REVIEWED"
    assert updated_fdr["branch_name"] == "Connaught Place Specialized Branch"
    assert float(updated_fdr["interest_rate"]) == 7.50

    # Verify underlying extraction record is marked reviewed with 100% human confidence
    ext_check = client.get(f"/api/v1/fdr/{fdr_id}/extraction", headers=headers).json()
    assert ext_check["is_reviewed"] == 1
    assert ext_check["extracted_fields"]["branch_name"] == "Connaught Place Specialized Branch"
    assert ext_check["field_confidences"]["branch_name"] == 100.0

def test_ocr_multi_tenant_isolation_and_role_access():
    """Verify that institutions cannot access other institutions' OCR extractions, while Scrutiny Officers and Auditors can."""
    inst1_token = get_auth_token("inst_admin@fdrsetu.gov.in")
    inst2_token = get_auth_token("inst2_admin@fdrsetu.gov.in")
    officer_token = get_auth_token("scrutiny_officer@fdrsetu.gov.in")
    auditor_token = get_auth_token("auditor@fdrsetu.gov.in")

    headers1 = {"Authorization": f"Bearer {inst1_token}"}
    headers2 = {"Authorization": f"Bearer {inst2_token}"}
    headers_officer = {"Authorization": f"Bearer {officer_token}"}
    headers_auditor = {"Authorization": f"Bearer {auditor_token}"}

    uid = uuid.uuid4().hex[:6].upper()
    fdr_no = f"FDR-TENANT-{uid}"

    # Institution 1 creates FDR & uploads & extracts
    res = client.post("/api/v1/fdr", json={
        "fdr_number": fdr_no,
        "bank_name": "Canara Bank",
        "branch_name": "Kashmere Gate",
        "ifsc_code": "CNRB0001234",
        "deposit_amount": "2500000.00",
        "issue_date": "2024-03-01",
        "maturity_date": "2029-03-01"
    }, headers=headers1)
    fdr_id = res.json()["id"]

    pdf_bytes = generate_fdr_pdf(fdr_number=fdr_no, bank_name="CANARA BANK", ifsc="CNRB0001234")
    client.post(
        f"/api/v1/fdr/{fdr_id}/documents",
        data={"document_type": "PRIMARY_INSTRUMENT"},
        files={"file": (f"{fdr_no}.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers1
    )
    client.post(f"/api/v1/fdr/{fdr_id}/extract", headers=headers1)

    # Institution 2 MUST NOT be able to view or edit Institution 1's OCR extraction
    forbidden_get = client.get(f"/api/v1/fdr/{fdr_id}/extraction", headers=headers2)
    assert forbidden_get.status_code == 403

    forbidden_patch = client.patch(
        f"/api/v1/fdr/{fdr_id}/extraction",
        json={"corrected_fields": {"bank_name": "Hacked Bank"}},
        headers=headers2
    )
    assert forbidden_patch.status_code == 403

    # Scrutiny Officer CAN view extraction
    officer_get = client.get(f"/api/v1/fdr/{fdr_id}/extraction", headers=headers_officer)
    assert officer_get.status_code == 200
    assert officer_get.json()["fdr_id"] == fdr_id

    # Auditor CAN view extraction
    auditor_get = client.get(f"/api/v1/fdr/{fdr_id}/extraction", headers=headers_auditor)
    assert auditor_get.status_code == 200
    assert auditor_get.json()["fdr_id"] == fdr_id
