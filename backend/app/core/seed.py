import logging
from sqlalchemy.orm import Session
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
import app.models
from app.models.user import Role, User
from app.models.institution import Institution
from app.models.audit import AuditLog

logger = logging.getLogger("fdrsetu.seed")

ROLES_DATA = [
    {
        "name": "ROLE_INSTITUTION_ADMIN",
        "description": "Institution Administrator: Submits and manages institutional FDRs, responds to scrutiny observations, initiates renewals and refund petitions."
    },
    {
        "name": "ROLE_SCRUTINY_OFFICER",
        "description": "AICTE Scrutiny Officer: Reviews submitted instruments, cross-checks OCR extractions, flags discrepancies, and recommends decisions."
    },
    {
        "name": "ROLE_APPROVING_AUTHORITY",
        "description": "AICTE Approving Authority: Reviews scrutiny findings and grants statutory approval or rejection on FDRs and releases."
    },
    {
        "name": "ROLE_SYSTEM_ADMIN",
        "description": "System Administrator: Configures rules, oversees institution approvals, manages user security and notification schedules."
    },
    {
        "name": "ROLE_AUDITOR",
        "description": "Auditor: Read-only regulatory oversight of immutable audit trails, verification results, and historical approvals."
    }
]

DEMO_USERS = [
    {
        "username": "inst_admin",
        "email": "inst_admin@fdrsetu.gov.in",
        "full_name": "Dr. Rajeshwar Sharma",
        "designation": "Registrar (Delhi Institute of Tech)",
        "phone_number": "+91 98765 43210",
        "role_name": "ROLE_INSTITUTION_ADMIN",
        "is_institution_user": True
    },
    {
        "username": "inst2_admin",
        "email": "inst2_admin@fdrsetu.gov.in",
        "full_name": "Dr. Sneha Kulkarni",
        "designation": "Registrar (Mumbai Institute of Tech)",
        "phone_number": "+91 98999 88776",
        "role_name": "ROLE_INSTITUTION_ADMIN",
        "is_institution_user": True
    },
    {
        "username": "scrutiny_officer",
        "email": "scrutiny_officer@fdrsetu.gov.in",
        "full_name": "Smt. Sunita Verma",
        "designation": "AICTE Senior Scrutiny Officer",
        "phone_number": "+91 98111 22334",
        "role_name": "ROLE_SCRUTINY_OFFICER",
        "is_institution_user": False
    },
    {
        "username": "approving_auth",
        "email": "approving_auth@fdrsetu.gov.in",
        "full_name": "Prof. Anil K. Sahasrabudhe",
        "designation": "AICTE Competent Approving Authority",
        "phone_number": "+91 98222 33445",
        "role_name": "ROLE_APPROVING_AUTHORITY",
        "is_institution_user": False
    },
    {
        "username": "sys_admin",
        "email": "sys_admin@fdrsetu.gov.in",
        "full_name": "Vikramaditya Rao",
        "designation": "Principal System Architect & Admin",
        "phone_number": "+91 98333 44556",
        "role_name": "ROLE_SYSTEM_ADMIN",
        "is_institution_user": False
    },
    {
        "username": "auditor",
        "email": "auditor@fdrsetu.gov.in",
        "full_name": "Harish Chandra Joshi",
        "designation": "Chief Compliance Officer & Statutory Auditor",
        "phone_number": "+91 98444 55667",
        "role_name": "ROLE_AUDITOR",
        "is_institution_user": False
    }
]

from decimal import Decimal
from datetime import date
import hashlib
import os
import uuid
from app.core.config import settings
from app.models.fdr import FDRRecord, FDRDocument
from app.models.verification import VerificationRule

DEFAULT_VERIFICATION_RULES = [
    {
        "rule_code": "RULE_MANDATORY_FIELDS",
        "name": "Mandatory Statutory Fields",
        "description": "Verifies that all required statutory fields (FDR number, Bank, Branch, IFSC, Amount, Issue Date, Maturity Date) are provided and non-empty.",
        "severity": "CRITICAL",
        "is_enabled": True,
        "parameters": {"required_fields": ["fdr_number", "bank_name", "branch_name", "ifsc_code", "deposit_amount", "issue_date", "maturity_date"]}
    },
    {
        "rule_code": "RULE_FDR_NUMBER",
        "name": "FDR Number Format & Sanitization",
        "description": "Ensures the FDR number conforms to banking conventions (minimum 5 characters, alphanumeric/dashes, not generic dummy strings).",
        "severity": "CRITICAL",
        "is_enabled": True,
        "parameters": {"min_length": 5, "disallowed_patterns": ["000000", "123456", "DUMMY", "TEST"]}
    },
    {
        "rule_code": "RULE_DATE_CONSISTENCY",
        "name": "Date Chronology & Validity",
        "description": "Verifies that the deposit issue date is not in the future and the maturity date strictly follows the issue date.",
        "severity": "CRITICAL",
        "is_enabled": True,
        "parameters": {"allow_same_day_issue": True}
    },
    {
        "rule_code": "RULE_MATURITY_TENURE",
        "name": "Statutory Minimum Maturity Tenure",
        "description": "Verifies that the FDR maturity period satisfies AICTE Approval Process Handbook (APH) regulations (minimum 12 months).",
        "severity": "HIGH",
        "is_enabled": True,
        "parameters": {"min_tenure_months": 12, "recommended_tenure_months": 60}
    },
    {
        "rule_code": "RULE_AMOUNT_CONSISTENCY",
        "name": "Deposit Amount & OCR Cross-Match",
        "description": "Ensures deposit sum meets the minimum statutory threshold (e.g. ₹ 1,00,000) and matches OCR-extracted document amount within tolerance.",
        "severity": "CRITICAL",
        "is_enabled": True,
        "parameters": {"min_deposit_amount": 100000.0, "tolerance_percentage": 1.0}
    },
    {
        "rule_code": "RULE_BANK_RECOGNITION",
        "name": "Scheduled Commercial Bank Recognition",
        "description": "Verifies that the issuing financial institution is an RBI-scheduled commercial bank recognized for AICTE security deposits.",
        "severity": "HIGH",
        "is_enabled": True,
        "parameters": {"disallow_unregistered_cooperatives": True}
    },
    {
        "rule_code": "RULE_IFSC_FORMAT",
        "name": "RBI IFSC Syntax & Prefix Verification",
        "description": "Validates the 11-character alphanumeric IFSC code format (first 4 letters bank code, 5th character '0', last 6 alphanumeric branch code).",
        "severity": "HIGH",
        "is_enabled": True,
        "parameters": {"regex_pattern": "^[A-Z]{4}0[A-Z0-9]{6}$"}
    },
    {
        "rule_code": "RULE_BENEFICIARY_MATCH",
        "name": "Statutory Beneficiary Lien In Favour of AICTE",
        "description": "Ensures the fixed deposit instrument is pledged or marked in lien in favour of AICTE / Member Secretary, AICTE New Delhi.",
        "severity": "CRITICAL",
        "is_enabled": True,
        "parameters": {"required_keywords": ["AICTE", "MEMBER SECRETARY"]}
    },
    {
        "rule_code": "RULE_DUPLICATE_DETECTION",
        "name": "System-Wide Duplicate FDR Detection",
        "description": "Scans across all institutions and records to ensure the FDR certificate number or bank account combination has not been submitted elsewhere.",
        "severity": "CRITICAL",
        "is_enabled": True,
        "parameters": {"check_across_all_tenants": True}
    },
    {
        "rule_code": "RULE_MISSING_DOCUMENT",
        "name": "Primary Instrument Document Vault Audit",
        "description": "Verifies that at least one cryptographically validated PRIMARY_INSTRUMENT document is attached with a non-zero payload.",
        "severity": "CRITICAL",
        "is_enabled": True,
        "parameters": {"required_document_types": ["PRIMARY_INSTRUMENT"]}
    },
    {
        "rule_code": "RULE_TENANT_BOUNDARY",
        "name": "Multi-Tenant Ownership & Boundary Check",
        "description": "Verifies that the submitting institution profile is ACTIVE, AICTE-approved, and owns the recorded security deposit.",
        "severity": "CRITICAL",
        "is_enabled": True,
        "parameters": {"require_active_account": True}
    },
    {
        "rule_code": "RULE_ANOMALY_DETECTION",
        "name": "Statistical & Heuristic Anomaly Detection",
        "description": "Flags unusual patterns such as extreme deposit amounts (> ₹10 Cr), abnormal interest rates (> 12% or < 3%), or severely degraded OCR confidence (< 60%).",
        "severity": "MEDIUM",
        "is_enabled": True,
        "parameters": {
            "max_deposit_amount": 100000000.0,
            "min_interest_rate": 3.0,
            "max_interest_rate": 12.0,
            "min_ocr_confidence": 60.0,
            "max_tenure_years": 15
        }
    }
]

MINIMAL_VALID_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n"

def seed_sample_fdrs(db: Session, demo_inst: Institution, admin_user: User, custom_samples: list = None):
    """Seeds initial demonstration FDR instruments and attached PDF documents."""
    fdr_samples = custom_samples or [
        {
            "fdr_number": "FDR-SBI-2024-9871",
            "bank_name": "State Bank of India",
            "branch_name": "Vasant Kunj Institutional Area",
            "ifsc_code": "SBIN0001234",
            "deposit_amount": Decimal("3500000.00"),
            "issue_date": date(2024, 7, 15),
            "maturity_date": date(2027, 7, 14),
            "interest_rate": Decimal("7.10"),
            "beneficiary": "Member Secretary, AICTE / Regional Officer, AICTE",
            "joint_holder": "Delhi Institute of Technology & Advanced Studies",
            "instrument_type": "Fixed Deposit Receipt",
            "is_auto_renewal": False,
            "ocr_status": "COMPLETED",
            "verification_status": "PASSED",
            "lifecycle_status": "APPROVED_ACTIVE",
            "doc_filename": "SBI_FDR_35L_OfficialReceipt.pdf"
        },
        {
            "fdr_number": "FDR-PNB-2024-4412",
            "bank_name": "Punjab National Bank",
            "branch_name": "Connaught Place",
            "ifsc_code": "PUNB0011223",
            "deposit_amount": Decimal("2500000.00"),
            "issue_date": date(2024, 8, 10),
            "maturity_date": date(2027, 8, 9),
            "interest_rate": Decimal("7.25"),
            "beneficiary": "Member Secretary, AICTE / Regional Officer, AICTE",
            "joint_holder": "Delhi Institute of Technology & Advanced Studies",
            "instrument_type": "Fixed Deposit Receipt",
            "is_auto_renewal": False,
            "ocr_status": "COMPLETED",
            "verification_status": "PASSED",
            "lifecycle_status": "APPROVED_ACTIVE",
            "doc_filename": "PNB_FDR_25L_OfficialReceipt.pdf"
        },
        {
            "fdr_number": "FDR-HDFC-2025-1029",
            "bank_name": "HDFC Bank",
            "branch_name": "Hauz Khas",
            "ifsc_code": "HDFC0004321",
            "deposit_amount": Decimal("2500000.00"),
            "issue_date": date(2025, 1, 12),
            "maturity_date": date(2026, 1, 11),
            "interest_rate": Decimal("7.00"),
            "beneficiary": "Member Secretary, AICTE / Regional Officer, AICTE",
            "joint_holder": "Delhi Institute of Technology & Advanced Studies",
            "instrument_type": "Fixed Deposit Receipt",
            "is_auto_renewal": True,
            "ocr_status": "COMPLETED",
            "verification_status": "PASSED_WITH_WARNINGS",
            "lifecycle_status": "UNDER_SCRUTINY",
            "doc_filename": "HDFC_FDR_25L_DepositCertificate.pdf"
        },
        {
            "fdr_number": "FDR-CANARA-2025-5591",
            "bank_name": "Canara Bank",
            "branch_name": "Saket District Centre",
            "ifsc_code": "CNRB0009876",
            "deposit_amount": Decimal("1500000.00"),
            "issue_date": date(2025, 2, 1),
            "maturity_date": date(2028, 1, 31),
            "interest_rate": Decimal("6.90"),
            "beneficiary": "Member Secretary, AICTE / Regional Officer, AICTE",
            "joint_holder": "Delhi Institute of Technology & Advanced Studies",
            "instrument_type": "Fixed Deposit Receipt",
            "is_auto_renewal": False,
            "ocr_status": "MANUALLY_ENTERED",
            "verification_status": "UNVERIFIED",
            "lifecycle_status": "DRAFT",
            "doc_filename": "CanaraBank_FDR_15L_DraftCopy.pdf"
        }
    ]

    dest_dir = os.path.join(settings.UPLOAD_DIR, "2026")
    os.makedirs(dest_dir, exist_ok=True)
    pdf_hash = hashlib.sha256(MINIMAL_VALID_PDF).hexdigest()

    for item in fdr_samples:
        existing_fdr = db.query(FDRRecord).filter(
            FDRRecord.fdr_number == item["fdr_number"],
            FDRRecord.bank_name == item["bank_name"]
        ).first()

        if not existing_fdr:
            fdr = FDRRecord(
                institution_id=demo_inst.id,
                submitted_by_id=admin_user.id,
                fdr_number=item["fdr_number"],
                bank_name=item["bank_name"],
                branch_name=item["branch_name"],
                ifsc_code=item["ifsc_code"],
                deposit_amount=item["deposit_amount"],
                issue_date=item["issue_date"],
                maturity_date=item["maturity_date"],
                interest_rate=item["interest_rate"],
                beneficiary=item["beneficiary"],
                joint_holder=item["joint_holder"],
                instrument_type=item["instrument_type"],
                is_auto_renewal=item["is_auto_renewal"],
                ocr_status=item["ocr_status"],
                verification_status=item["verification_status"],
                lifecycle_status=item["lifecycle_status"]
            )
            db.add(fdr)
            db.commit()
            db.refresh(fdr)

            # Create physical file and FDRDocument record
            stored_name = f"seed_{uuid.uuid4().hex[:12]}.pdf"
            file_path_on_disk = os.path.join(dest_dir, stored_name)
            with open(file_path_on_disk, "wb") as pf:
                pf.write(MINIMAL_VALID_PDF)

            rel_path = os.path.relpath(file_path_on_disk, settings.STORAGE_DIR)
            doc = FDRDocument(
                fdr_id=fdr.id,
                institution_id=demo_inst.id,
                uploaded_by_id=admin_user.id,
                document_type="FDR_INSTRUMENT",
                original_filename=item["doc_filename"],
                stored_filename=stored_name,
                file_path=rel_path,
                file_size=len(MINIMAL_VALID_PDF),
                mime_type="application/pdf",
                sha256_hash=pdf_hash
            )
            db.add(doc)
            db.commit()
            logger.info(f"Seeded FDR: {fdr.fdr_number} ({fdr.bank_name}) with document {doc.original_filename}")

def init_db(db: Session = None):
    """
    Initializes database tables and seeds core roles, demo institution, and demo user accounts.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
        
    try:
        # Create all tables if they don't exist
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified.")

        # 1. Seed Roles
        role_map = {}
        for r_data in ROLES_DATA:
            role = db.query(Role).filter(Role.name == r_data["name"]).first()
            if not role:
                role = Role(name=r_data["name"], description=r_data["description"])
                db.add(role)
                db.commit()
                db.refresh(role)
                logger.info(f"Seeded role: {role.name}")
            role_map[role.name] = role

        # 2. Seed Default Institution
        demo_inst = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-98765432").first()
        if not demo_inst:
            demo_inst = Institution(
                aicte_id="AICTE-1-98765432",
                name="Delhi Institute of Technology & Advanced Studies",
                institution_type="Engineering & Technology",
                address="Plot 14, Sector 7, Institutional Area, Vasant Kunj",
                state="Delhi",
                district="South West Delhi",
                pin_code="110070",
                contact_person="Dr. Rajeshwar Sharma",
                official_email="principal@ditas-delhi.edu.in",
                phone_number="+91 11 2612 3456",
                account_status="ACTIVE"
            )
            db.add(demo_inst)
            db.commit()
            db.refresh(demo_inst)
            logger.info(f"Seeded demo institution: {demo_inst.name} ({demo_inst.aicte_id})")

        # 3. Seed Demo Users
        common_password_hash = hash_password("Admin@123")
        for u_data in DEMO_USERS:
            user = db.query(User).filter(User.email == u_data["email"]).first()
            if not user:
                role = role_map.get(u_data["role_name"])
                user = User(
                    username=u_data["username"],
                    email=u_data["email"],
                    full_name=u_data["full_name"],
                    designation=u_data["designation"],
                    phone_number=u_data["phone_number"],
                    hashed_password=common_password_hash,
                    role_id=role.id,
                    institution_id=demo_inst.id if u_data["is_institution_user"] else None,
                    is_active=True,
                    is_verified=True
                )
                db.add(user)
                db.commit()
                logger.info(f"Seeded demo user: {user.email} [{u_data['role_name']}]")
                
        # 4. Seed Demonstration FDR Instruments
        inst_admin = db.query(User).filter(User.email == "inst_admin@fdrsetu.gov.in").first()
        if demo_inst and inst_admin:
            seed_sample_fdrs(db, demo_inst, inst_admin)

        # 5. Seed Secondary Institution for multi-tenant isolation testing
        demo_inst2 = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-44556677").first()
        if not demo_inst2:
            demo_inst2 = Institution(
                aicte_id="AICTE-1-44556677",
                name="Mumbai Institute of Technology & Research",
                institution_type="Engineering & Technology",
                address="Sector 15, Powai, Andheri East",
                state="Maharashtra",
                district="Mumbai Suburban",
                pin_code="400076",
                contact_person="Dr. Sneha Kulkarni",
                official_email="registrar@mitr-mumbai.edu.in",
                phone_number="+91 22 2576 8900",
                account_status="ACTIVE"
            )
            db.add(demo_inst2)
            db.commit()
            db.refresh(demo_inst2)
            logger.info(f"Seeded demo institution 2: {demo_inst2.name}")

        inst2_user = db.query(User).filter(User.email == "inst2_admin@fdrsetu.gov.in").first()
        if not inst2_user:
            inst2_user = User(
                username="inst2_admin",
                email="inst2_admin@fdrsetu.gov.in",
                full_name="Dr. Sneha Kulkarni",
                designation="Registrar",
                phone_number="+91 98999 88776",
                hashed_password=common_password_hash,
                role_id=role_map["ROLE_INSTITUTION_ADMIN"].id,
                institution_id=demo_inst2.id,
                is_active=True,
                is_verified=True
            )
            db.add(inst2_user)
            db.commit()
            db.refresh(inst2_user)
            logger.info("Seeded demo user: inst2_admin@fdrsetu.gov.in")

        if demo_inst2 and inst2_user:
            seed_sample_fdrs(db, demo_inst2, inst2_user, [
                {
                    "fdr_number": "FDR-BOB-2024-7711",
                    "bank_name": "Bank of Baroda",
                    "branch_name": "Nariman Point",
                    "ifsc_code": "BARB0000001",
                    "deposit_amount": Decimal("5000000.00"),
                    "issue_date": date(2024, 6, 1),
                    "maturity_date": date(2027, 5, 31),
                    "interest_rate": Decimal("7.20"),
                    "beneficiary": "Member Secretary, AICTE / Regional Officer, AICTE",
                    "joint_holder": "Mumbai Institute of Technology & Research",
                    "instrument_type": "Fixed Deposit Receipt",
                    "is_auto_renewal": False,
                    "ocr_status": "COMPLETED",
                    "verification_status": "PASSED",
                    "lifecycle_status": "APPROVED_ACTIVE",
                    "doc_filename": "BOB_FDR_50L_OfficialReceipt.pdf"
                }
            ])

        # 6. Seed Configurable Verification Rules
        for r_spec in DEFAULT_VERIFICATION_RULES:
            existing_rule = db.query(VerificationRule).filter(VerificationRule.rule_code == r_spec["rule_code"]).first()
            if not existing_rule:
                rule_obj = VerificationRule(
                    rule_code=r_spec["rule_code"],
                    name=r_spec["name"],
                    description=r_spec["description"],
                    severity=r_spec["severity"],
                    is_enabled=r_spec["is_enabled"],
                    parameters=r_spec["parameters"]
                )
                db.add(rule_obj)
        db.commit()
        logger.info(f"Seeded/verified {len(DEFAULT_VERIFICATION_RULES)} configurable verification rules.")

        logger.info("Database seeding successfully verified.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        db.rollback()
        raise e
    finally:
        if close_db:
            db.close()

if __name__ == "__main__":
    init_db()
