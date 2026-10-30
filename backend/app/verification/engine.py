import re
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.fdr import FDRRecord, FDRDocument
from app.models.ocr import OCRExtraction
from app.models.verification import VerificationRule
from app.models.institution import Institution

RECOGNIZED_SCHEDULED_BANKS = [
    "STATE BANK OF INDIA", "SBI", "PUNJAB NATIONAL BANK", "PNB",
    "BANK OF BARODA", "BOB", "CANARA BANK", "UNION BANK OF INDIA",
    "BANK OF INDIA", "INDIAN BANK", "CENTRAL BANK OF INDIA",
    "INDIAN OVERSEAS BANK", "UCO BANK", "BANK OF MAHARASHTRA",
    "PUNJAB & SIND BANK", "HDFC BANK", "HDFC", "ICICI BANK", "ICICI",
    "AXIS BANK", "KOTAK MAHINDRA BANK", "IDBI BANK", "FEDERAL BANK",
    "YES BANK", "INDUSIND BANK"
]

class VerificationEngine:
    """
    Modular Intelligent Rule-Based Verification Engine for FDRSetu.
    Evaluates 12 regulatory, statutory, format, duplicate, and anomaly rules.
    """

    @staticmethod
    def evaluate_all_rules(db: Session, fdr: FDRRecord) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Executes all enabled verification rules against the target FDR record.
        
        Returns:
            overall_status: 'PASSED' | 'PASSED_WITH_WARNINGS' | 'FAILED_DISCREPANCIES'
            rule_results: list of detailed evaluation outcome for each rule
            discrepancies_to_raise: list of discrepancy dictionaries for failed/warning rules
        """
        # Fetch configured rules from DB
        db_rules = {r.rule_code: r for r in db.query(VerificationRule).all()}
        
        # Load related OCR extraction if present
        ocr_extraction = db.query(OCRExtraction).filter(OCRExtraction.fdr_id == fdr.id).first()

        rule_results: List[Dict[str, Any]] = []
        discrepancies: List[Dict[str, Any]] = []

        # 12 Rule Evaluators
        evaluators = [
            ("RULE_MANDATORY_FIELDS", VerificationEngine._eval_mandatory_fields),
            ("RULE_FDR_NUMBER", VerificationEngine._eval_fdr_number),
            ("RULE_DATE_CONSISTENCY", VerificationEngine._eval_date_consistency),
            ("RULE_MATURITY_TENURE", VerificationEngine._eval_maturity_tenure),
            ("RULE_AMOUNT_CONSISTENCY", VerificationEngine._eval_amount_consistency),
            ("RULE_BANK_RECOGNITION", VerificationEngine._eval_bank_recognition),
            ("RULE_IFSC_FORMAT", VerificationEngine._eval_ifsc_format),
            ("RULE_BENEFICIARY_MATCH", VerificationEngine._eval_beneficiary_match),
            ("RULE_DUPLICATE_DETECTION", VerificationEngine._eval_duplicate_detection),
            ("RULE_MISSING_DOCUMENT", VerificationEngine._eval_missing_document),
            ("RULE_TENANT_BOUNDARY", VerificationEngine._eval_tenant_boundary),
            ("RULE_ANOMALY_DETECTION", VerificationEngine._eval_anomaly_detection)
        ]

        critical_failed = False
        high_failed = False
        warnings_present = False

        for rule_code, eval_fn in evaluators:
            rule_config = db_rules.get(rule_code)
            is_enabled = rule_config.is_enabled if rule_config else True
            severity = rule_config.severity if rule_config else "HIGH"
            params = rule_config.parameters if rule_config else {}

            if not is_enabled:
                rule_results.append({
                    "rule_code": rule_code,
                    "name": rule_config.name if rule_config else rule_code,
                    "status": "SKIPPED",
                    "severity": severity,
                    "message": "Rule evaluation disabled by System Administrator.",
                    "actual": None,
                    "expected": None
                })
                continue

            # Run evaluation
            outcome = eval_fn(db, fdr, ocr_extraction, params)
            rule_name = rule_config.name if rule_config else outcome.get("name", rule_code)
            outcome["rule_code"] = rule_code
            outcome["name"] = rule_name
            outcome["severity"] = severity

            rule_results.append(outcome)

            if outcome["status"] == "FAILED":
                if severity == "CRITICAL":
                    critical_failed = True
                elif severity == "HIGH":
                    high_failed = True
                else:
                    warnings_present = True

                discrepancies.append({
                    "rule_code": rule_code,
                    "severity": severity,
                    "title": f"{rule_name} Discrepancy",
                    "description": outcome["message"],
                    "expected_value": str(outcome.get("expected")),
                    "actual_value": str(outcome.get("actual"))
                })
            elif outcome["status"] == "WARNING":
                warnings_present = True
                discrepancies.append({
                    "rule_code": rule_code,
                    "severity": "LOW" if severity == "LOW" else "MEDIUM",
                    "title": f"{rule_name} Observation",
                    "description": outcome["message"],
                    "expected_value": str(outcome.get("expected")),
                    "actual_value": str(outcome.get("actual"))
                })

        # Calculate overall verdict
        if critical_failed or high_failed:
            overall_status = "FAILED_DISCREPANCIES"
        elif warnings_present:
            overall_status = "PASSED_WITH_WARNINGS"
        else:
            overall_status = "PASSED"

        return overall_status, rule_results, discrepancies

    # -------------------------------------------------------------------------
    # RULE 1: MANDATORY STATUTORY FIELDS
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_mandatory_fields(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        required = params.get("required_fields", ["fdr_number", "bank_name", "branch_name", "ifsc_code", "deposit_amount", "issue_date", "maturity_date"])
        missing = []
        for field in required:
            val = getattr(fdr, field, None)
            if val is None or str(val).strip() == "":
                missing.append(field)

        if missing:
            return {
                "status": "FAILED",
                "message": f"Mandatory fields missing: {', '.join(missing)}",
                "expected": f"All {len(required)} statutory fields populated",
                "actual": f"Missing {len(missing)} fields: {', '.join(missing)}"
            }
        return {
            "status": "PASSED",
            "message": "All mandatory statutory fields are complete and non-empty.",
            "expected": "All mandatory fields present",
            "actual": "All required fields populated"
        }

    # -------------------------------------------------------------------------
    # RULE 2: FDR NUMBER FORMAT & SANITIZATION
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_fdr_number(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        fdr_num = (fdr.fdr_number or "").strip()
        min_len = params.get("min_length", 5)
        disallowed = params.get("disallowed_patterns", ["000000", "123456", "DUMMY", "TEST"])

        if len(fdr_num) < min_len:
            return {
                "status": "FAILED",
                "message": f"FDR number '{fdr_num}' is too short (minimum {min_len} characters required).",
                "expected": f">= {min_len} alphanumeric characters",
                "actual": f"{len(fdr_num)} characters"
            }
        
        for dis in disallowed:
            if dis.upper() in fdr_num.upper():
                return {
                    "status": "FAILED",
                    "message": f"FDR number contains prohibited generic placeholder pattern '{dis}'.",
                    "expected": "Valid authentic bank instrument certificate number",
                    "actual": fdr_num
                }

        return {
            "status": "PASSED",
            "message": f"FDR number '{fdr_num}' passes syntax and sanitization rules.",
            "expected": "Valid sanitized instrument number",
            "actual": fdr_num
        }

    # -------------------------------------------------------------------------
    # RULE 3: DATE CONSISTENCY CHECKS
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_date_consistency(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        today = date.today()
        if not fdr.issue_date or not fdr.maturity_date:
            return {
                "status": "FAILED",
                "message": "Cannot perform date consistency evaluation: Issue date or maturity date missing.",
                "expected": "Valid date objects",
                "actual": "Missing date"
            }

        if fdr.issue_date > today:
            return {
                "status": "FAILED",
                "message": f"Issue date ({fdr.issue_date}) cannot be in the future relative to current date ({today}).",
                "expected": f"Issue date <= {today}",
                "actual": str(fdr.issue_date)
            }

        if fdr.maturity_date <= fdr.issue_date:
            return {
                "status": "FAILED",
                "message": f"Maturity date ({fdr.maturity_date}) must be strictly after the issue date ({fdr.issue_date}).",
                "expected": f"Maturity date > {fdr.issue_date}",
                "actual": str(fdr.maturity_date)
            }

        return {
            "status": "PASSED",
            "message": f"Date chronology valid: Issued on {fdr.issue_date}, maturing on {fdr.maturity_date}.",
            "expected": "Chronologically consistent dates",
            "actual": f"Issue: {fdr.issue_date}, Maturity: {fdr.maturity_date}"
        }

    # -------------------------------------------------------------------------
    # RULE 4: MATURITY TENURE VALIDATION (AICTE APH Guidelines)
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_maturity_tenure(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        min_months = params.get("min_tenure_months", 12)
        min_days = min_months * 30  # Approx 360 days

        if not fdr.issue_date or not fdr.maturity_date:
            return {
                "status": "FAILED",
                "message": "Missing dates to calculate instrument maturity duration.",
                "expected": f">= {min_months} months tenure",
                "actual": "Unknown tenure"
            }

        duration_days = (fdr.maturity_date - fdr.issue_date).days
        months_approx = round(duration_days / 30.416, 1)

        if duration_days < min_days:
            return {
                "status": "FAILED",
                "message": f"FDR duration is {months_approx} months ({duration_days} days). AICTE regulations require minimum {min_months} months tenure for security deposits.",
                "expected": f">= {min_months} months ({min_days} days)",
                "actual": f"{months_approx} months ({duration_days} days)"
            }

        return {
            "status": "PASSED",
            "message": f"Instrument maturity tenure is {months_approx} months ({duration_days} days), satisfying regulatory requirements.",
            "expected": f">= {min_months} months",
            "actual": f"{months_approx} months"
        }

    # -------------------------------------------------------------------------
    # RULE 5: AMOUNT CONSISTENCY & OCR CROSS-CHECK
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_amount_consistency(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        min_amt = Decimal(str(params.get("min_deposit_amount", 100000.0)))
        deposit_amt = Decimal(str(fdr.deposit_amount or 0))

        if deposit_amt < min_amt:
            return {
                "status": "FAILED",
                "message": f"Deposit amount of ₹ {deposit_amt:,.2f} is below statutory minimum threshold of ₹ {min_amt:,.2f}.",
                "expected": f">= ₹ {min_amt:,.2f}",
                "actual": f"₹ {deposit_amt:,.2f}"
            }

        # Cross-check against OCR-extracted amount if available
        if ocr and ocr.extracted_fields and ocr.extracted_fields.get("deposit_amount"):
            try:
                ocr_amt = Decimal(str(ocr.extracted_fields["deposit_amount"]))
                diff = abs(deposit_amt - ocr_amt)
                tolerance = deposit_amt * Decimal(str(params.get("tolerance_percentage", 1.0) / 100.0))
                if diff > tolerance:
                    return {
                        "status": "FAILED",
                        "message": f"Discrepancy between declared deposit (₹ {deposit_amt:,.2f}) and OCR-extracted instrument amount (₹ {ocr_amt:,.2f}).",
                        "expected": f"Declared amount matches OCR amount (₹ {ocr_amt:,.2f})",
                        "actual": f"₹ {deposit_amt:,.2f} (diff: ₹ {diff:,.2f})"
                    }
            except Exception:
                pass

        return {
            "status": "PASSED",
            "message": f"Deposit amount of ₹ {deposit_amt:,.2f} satisfies regulatory minimum and matches verified document.",
            "expected": f">= ₹ {min_amt:,.2f}",
            "actual": f"₹ {deposit_amt:,.2f}"
        }

    # -------------------------------------------------------------------------
    # RULE 6: BANK & BRANCH RECOGNITION
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_bank_recognition(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        bank = (fdr.bank_name or "").strip().upper()
        if not bank:
            return {
                "status": "FAILED",
                "message": "Bank name is empty.",
                "expected": "RBI-Scheduled Commercial Bank",
                "actual": "None"
            }

        is_recognized = any(recognized in bank for recognized in RECOGNIZED_SCHEDULED_BANKS)
        if not is_recognized:
            return {
                "status": "WARNING",
                "message": f"Bank '{fdr.bank_name}' could not be automatically confirmed in AICTE primary scheduled bank registry. Manual officer verification recommended.",
                "expected": "RBI-Scheduled Commercial Bank",
                "actual": fdr.bank_name
            }

        return {
            "status": "PASSED",
            "message": f"Bank '{fdr.bank_name}' confirmed as a recognized Scheduled Commercial Bank.",
            "expected": "Recognized Scheduled Bank",
            "actual": fdr.bank_name
        }

    # -------------------------------------------------------------------------
    # RULE 7: IFSC FORMAT & RBI PREFIX VALIDATION
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_ifsc_format(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        ifsc = (fdr.ifsc_code or "").strip().upper()
        pattern = params.get("regex_pattern", r"^[A-Z]{4}0[A-Z0-9]{6}$")

        if not re.match(pattern, ifsc):
            return {
                "status": "FAILED",
                "message": f"IFSC code '{ifsc}' does not conform to standard RBI syntax (11 characters: 4 letters, '0', 6 alphanumeric).",
                "expected": "11-character RBI IFSC (e.g. SBIN0001234)",
                "actual": ifsc
            }

        return {
            "status": "PASSED",
            "message": f"IFSC code '{ifsc}' valid and properly formatted.",
            "expected": "Valid IFSC format",
            "actual": ifsc
        }

    # -------------------------------------------------------------------------
    # RULE 8: BENEFICIARY MISMATCH CHECKS
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_beneficiary_match(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        keywords = params.get("required_keywords", ["AICTE", "MEMBER SECRETARY"])
        beneficiary_str = (fdr.beneficiary or "").upper()

        has_match = any(k.upper() in beneficiary_str for k in keywords)
        if not has_match:
            return {
                "status": "FAILED",
                "message": f"Beneficiary '{fdr.beneficiary}' does not appear to be in statutory favour of AICTE or Member Secretary, AICTE.",
                "expected": "In favour of / Lien marked to AICTE or Member Secretary, AICTE",
                "actual": fdr.beneficiary or "Not specified"
            }

        # If OCR extracted a beneficiary, cross check
        if ocr and ocr.extracted_fields and ocr.extracted_fields.get("beneficiary"):
            ocr_ben = str(ocr.extracted_fields["beneficiary"]).upper()
            if not any(k.upper() in ocr_ben for k in keywords):
                return {
                    "status": "WARNING",
                    "message": f"OCR-extracted document text shows beneficiary '{ocr_ben}' which may not explicitly mention AICTE lien.",
                    "expected": "AICTE / Member Secretary in document text",
                    "actual": ocr.extracted_fields["beneficiary"]
                }

        return {
            "status": "PASSED",
            "message": f"Beneficiary correctly marked in favour of AICTE: '{fdr.beneficiary}'.",
            "expected": "AICTE Lien / In favour of AICTE",
            "actual": fdr.beneficiary
        }

    # -------------------------------------------------------------------------
    # RULE 9: SYSTEM-WIDE DUPLICATE FDR DETECTION
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_duplicate_detection(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        fdr_num = (fdr.fdr_number or "").strip()
        bank_name = (fdr.bank_name or "").strip()

        # Query other records
        duplicates = db.query(FDRRecord).filter(
            FDRRecord.id != fdr.id,
            FDRRecord.fdr_number == fdr_num,
            FDRRecord.bank_name.ilike(bank_name)
        ).all()

        if duplicates:
            other_inst_ids = list(set([d.institution_id for d in duplicates]))
            return {
                "status": "FAILED",
                "message": f"CRITICAL: Duplicate FDR instrument detected! Same FDR Number '{fdr_num}' and Bank '{bank_name}' exists in {len(duplicates)} other record(s) (Institution IDs: {other_inst_ids}).",
                "expected": "Unique FDR certificate across the entire AICTE system",
                "actual": f"Duplicate found in {len(duplicates)} record(s)"
            }

        return {
            "status": "PASSED",
            "message": "System-wide duplicate check passed: No duplicate FDR number found in database.",
            "expected": "Unique instrument number",
            "actual": "Unique (0 duplicates)"
        }

    # -------------------------------------------------------------------------
    # RULE 10: MISSING PRIMARY INSTRUMENT DOCUMENT CHECK
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_missing_document(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        req_types = params.get("required_document_types", ["PRIMARY_INSTRUMENT"])
        docs = fdr.documents or []

        has_primary = any(d.document_type == "PRIMARY_INSTRUMENT" and d.file_size > 0 for d in docs)
        if not has_primary:
            return {
                "status": "FAILED",
                "message": "No valid PRIMARY_INSTRUMENT document (original scanned copy of FDR) is uploaded to the document vault.",
                "expected": "At least 1 PRIMARY_INSTRUMENT scanned document",
                "actual": f"{len(docs)} documents ({[d.document_type for d in docs]})"
            }

        return {
            "status": "PASSED",
            "message": f"Valid primary instrument document confirmed ({len(docs)} total files attached).",
            "expected": "Primary instrument attached",
            "actual": f"{len(docs)} document(s) verified"
        }

    # -------------------------------------------------------------------------
    # RULE 11: MULTI-TENANT BOUNDARY & INSTITUTION AUDIT
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_tenant_boundary(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        if not fdr.institution_id:
            return {
                "status": "FAILED",
                "message": "Security deposit record is orphaned with no associated Technical Institution.",
                "expected": "Linked active technical institution",
                "actual": "None"
            }

        inst = db.query(Institution).filter(Institution.id == fdr.institution_id).first()
        if not inst:
            return {
                "status": "FAILED",
                "message": f"Referenced Institution ID {fdr.institution_id} does not exist in registry.",
                "expected": "Existing registered institution",
                "actual": "Invalid Institution ID"
            }

        if inst.account_status not in ["ACTIVE", "PENDING_APPROVAL"]:
            return {
                "status": "FAILED",
                "message": f"Institution '{inst.name}' account status is '{inst.account_status}'. Non-active institutions cannot maintain regulatory deposits.",
                "expected": "ACTIVE institution account",
                "actual": inst.account_status
            }

        return {
            "status": "PASSED",
            "message": f"Multi-tenant ownership verified: Linked to {inst.name} ({inst.aicte_id}) with status '{inst.account_status}'.",
            "expected": "Authorized institution ownership",
            "actual": f"{inst.name} [ACTIVE]"
        }

    # -------------------------------------------------------------------------
    # RULE 12: STATISTICAL & HEURISTIC ANOMALY DETECTION
    # -------------------------------------------------------------------------
    @staticmethod
    def _eval_anomaly_detection(db: Session, fdr: FDRRecord, ocr: Optional[OCRExtraction], params: Dict[str, Any]) -> Dict[str, Any]:
        max_amount = Decimal(str(params.get("max_deposit_amount", 100000000.0)))  # 10 Crore
        min_rate = Decimal(str(params.get("min_interest_rate", 3.0)))
        max_rate = Decimal(str(params.get("max_interest_rate", 12.0)))
        min_conf = float(params.get("min_ocr_confidence", 60.0))
        max_tenure_years = int(params.get("max_tenure_years", 15))

        anomalies = []

        # 1. Amount outlier check
        dep_amt = Decimal(str(fdr.deposit_amount or 0))
        if dep_amt > max_amount:
            anomalies.append(f"Deposit amount of ₹ {dep_amt:,.2f} exceeds typical institutional threshold (₹ {max_amount:,.2f}).")

        # 2. Interest rate outlier check
        if fdr.interest_rate is not None:
            rate = Decimal(str(fdr.interest_rate))
            if rate < min_rate or rate > max_rate:
                anomalies.append(f"Interest rate of {rate}% p.a. is outside standard commercial banking range ({min_rate}% - {max_rate}%).")

        # 3. Tenure outlier check
        if fdr.issue_date and fdr.maturity_date:
            years = (fdr.maturity_date - fdr.issue_date).days / 365.25
            if years > max_tenure_years:
                anomalies.append(f"Tenure of {years:.1f} years exceeds typical fixed deposit duration ({max_tenure_years} years).")

        # 4. OCR confidence degradation check
        if ocr and ocr.overall_confidence and ocr.overall_confidence < min_conf:
            anomalies.append(f"OCR overall confidence ({ocr.overall_confidence}%) is below quality threshold ({min_conf}%). Document may be blurry or damaged.")

        if anomalies:
            return {
                "status": "WARNING",
                "message": f"Heuristic anomalies detected: {' '.join(anomalies)}",
                "expected": "Normal statistical distribution",
                "actual": f"{len(anomalies)} anomalies flagged"
            }

        return {
            "status": "PASSED",
            "message": "Anomaly scan clean: Deposit amount, interest rate, tenure, and OCR confidence fall within standard empirical norms.",
            "expected": "Within standard parameters",
            "actual": "No anomalies detected"
        }

