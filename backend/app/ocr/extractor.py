import re
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger("fdrsetu.ocr.extractor")

RECOGNIZED_BANKS = [
    "State Bank of India",
    "Punjab National Bank",
    "Bank of Baroda",
    "Canara Bank",
    "Union Bank of India",
    "HDFC Bank",
    "ICICI Bank",
    "Axis Bank",
    "Kotak Mahindra Bank",
    "Indian Bank",
    "Central Bank of India",
    "Bank of India",
    "Indian Overseas Bank",
    "IDBI Bank",
    "Federal Bank"
]

class FieldExtractor:
    @staticmethod
    def extract_structured_fields(raw_text: str, base_confidence: float = 85.0) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Extracts structured FDR attributes from raw OCR text using multi-pattern regex,
        domain dictionaries, and calculates field-level confidence scores.
        
        Returns:
            (extracted_fields, field_confidences)
        """
        extracted = {}
        confidences = {}
        text_upper = raw_text.upper()

        # 1. Bank Name Extraction
        bank_found = None
        for bank in RECOGNIZED_BANKS:
            if bank.upper() in text_upper:
                bank_found = bank
                break
        if not bank_found:
            # Check abbreviations
            if "SBI" in text_upper:
                bank_found = "State Bank of India"
            elif "PNB" in text_upper:
                bank_found = "Punjab National Bank"
            elif "BOB" in text_upper:
                bank_found = "Bank of Baroda"
            elif "HDFC" in text_upper:
                bank_found = "HDFC Bank"
            elif "ICICI" in text_upper:
                bank_found = "ICICI Bank"

        if bank_found:
            extracted["bank_name"] = bank_found
            confidences["bank_name"] = round(min(base_confidence + 8.0, 99.0), 1)
        else:
            extracted["bank_name"] = None
            confidences["bank_name"] = 0.0

        # 2. FDR Number Extraction
        fdr_patterns = [
            r"\b(FDR-[A-Z0-9-]+)\b",
            r"(?:FDR|FD|RECEIPT|DEPOSIT\s*RECEIPT|ACCOUNT|A\/C|CERTIFICATE)[\s\w]*(?:NO|NUMBER|#)[\s.:#-]*([A-Z0-9\/-]{5,25})",
            r"(?:FDR|FD|RECEIPT|DEPOSIT\s*RECEIPT|ACCOUNT|A\/C)[\s.:#-]*([A-Z0-9\/-]{5,25})",
            r"\b([0-9]{9,16})\b" # standard bank account/FDR numeric string
        ]
        fdr_num = None
        fdr_conf = 0.0
        ignored_words = {"CERTIFICATE", "RECEIPT", "NUMBER", "ACCOUNT", "DEPOSIT", "BRANCH", "DETAILS"}
        for pattern in fdr_patterns:
            matches = re.finditer(pattern, raw_text, re.IGNORECASE)
            for match in matches:
                candidate = match.group(1).strip()
                if candidate.upper() in ignored_words:
                    continue
                if len(candidate) >= 5 and not candidate.startswith("00000"):
                    fdr_num = candidate
                    fdr_conf = round(min(base_confidence + 6.0, 97.0), 1)
                    break
            if fdr_num:
                break
        extracted["fdr_number"] = fdr_num
        confidences["fdr_number"] = fdr_conf

        # 3. IFSC Code Extraction
        ifsc_match = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", text_upper)
        if ifsc_match:
            extracted["ifsc_code"] = ifsc_match.group(1)
            confidences["ifsc_code"] = 99.0
        else:
            extracted["ifsc_code"] = None
            confidences["ifsc_code"] = 0.0

        # 4. Branch Name Extraction
        branch_match = re.search(r"(?:Branch|Br\.?)[\s.:-]*([A-Za-z0-9\s,.-]{3,35})", raw_text, re.IGNORECASE)
        if branch_match:
            branch_str = branch_match.group(1).strip().split("\n")[0]
            extracted["branch_name"] = branch_str.strip()
            confidences["branch_name"] = round(min(base_confidence + 3.0, 92.0), 1)
        else:
            extracted["branch_name"] = None
            confidences["branch_name"] = 0.0

        # 5. Principal Deposit Amount Extraction
        amount_patterns = [
            r"(?:₹|RS\.?|INR|AMOUNT|SUM\s*OF|PRINCIPAL)[\s.:]*([\d,]+(?:\.\d{2})?)",
            r"\b(?:RS\.?|INR)?\s*([0-9]{1,2}(?:,[0-9]{2})*(?:,[0-9]{3})(?:\.[0-9]{2})?)\b", # Indian numbering (e.g. 35,00,000)
            r"\b([1-9][0-9]{4,8}(?:\.00)?)\b" # Numeric plain
        ]
        amount_val = None
        amt_conf = 0.0
        for pat in amount_patterns:
            amt_match = re.search(pat, raw_text, re.IGNORECASE)
            if amt_match:
                clean_num = amt_match.group(1).replace(",", "").strip()
                try:
                    num_f = float(clean_num)
                    if num_f >= 10000: # FDR deposits are substantial
                        amount_val = num_f
                        amt_conf = round(min(base_confidence + 7.0, 98.0), 1)
                        break
                except ValueError:
                    continue
        extracted["deposit_amount"] = amount_val
        confidences["deposit_amount"] = amt_conf

        # 6. Dates Extraction (Issue Date & Maturity Date)
        dates = FieldExtractor._extract_dates(raw_text)
        if len(dates) >= 2:
            # Chronological sorting: issue date is earlier, maturity is later
            sorted_dates = sorted(dates)
            extracted["issue_date"] = sorted_dates[0].strftime("%Y-%m-%d")
            extracted["maturity_date"] = sorted_dates[-1].strftime("%Y-%m-%d")
            confidences["issue_date"] = round(min(base_confidence + 5.0, 95.0), 1)
            confidences["maturity_date"] = round(min(base_confidence + 5.0, 95.0), 1)
        elif len(dates) == 1:
            extracted["issue_date"] = dates[0].strftime("%Y-%m-%d")
            extracted["maturity_date"] = None
            confidences["issue_date"] = round(min(base_confidence + 4.0, 90.0), 1)
            confidences["maturity_date"] = 0.0
        else:
            extracted["issue_date"] = None
            extracted["maturity_date"] = None
            confidences["issue_date"] = 0.0
            confidences["maturity_date"] = 0.0

        # 7. Annual Interest Rate Extraction
        rate_match = re.search(r"(?:RATE|INT|ROI|PERCENT)[\s.:%]*([0-9]{1,2}(?:\.[0-9]{1,2})?)%?", raw_text, re.IGNORECASE)
        if rate_match:
            try:
                r_val = float(rate_match.group(1))
                if 2.0 <= r_val <= 15.0:
                    extracted["interest_rate"] = r_val
                    confidences["interest_rate"] = round(min(base_confidence + 4.0, 93.0), 1)
                else:
                    extracted["interest_rate"] = None
                    confidences["interest_rate"] = 0.0
            except ValueError:
                extracted["interest_rate"] = None
                confidences["interest_rate"] = 0.0
        else:
            extracted["interest_rate"] = None
            confidences["interest_rate"] = 0.0

        # 8. Beneficiary (AICTE)
        if "AICTE" in text_upper or "TECHNICAL EDUCATION" in text_upper:
            extracted["beneficiary"] = "Member Secretary, AICTE / Regional Officer, AICTE"
            confidences["beneficiary"] = 96.0
        else:
            extracted["beneficiary"] = "Member Secretary, AICTE"
            confidences["beneficiary"] = 70.0

        return extracted, confidences

    @staticmethod
    def _extract_dates(text: str) -> list:
        """Finds all calendar dates formatted as DD/MM/YYYY, DD-MM-YYYY, or DD Mon YYYY."""
        found_dates = []
        date_patterns = [
            (r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", "%d-%m-%Y"),
            (r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", "%Y-%m-%d"),
            (r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b", "%d %b %Y")
        ]

        for pattern, fmt in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                date_str = m.group(0).replace("/", "-").replace(".", "-")
                try:
                    if fmt == "%d-%m-%Y":
                        p = m.groups()
                        dt = datetime(int(p[2]), int(p[1]), int(p[0]))
                    elif fmt == "%Y-%m-%d":
                        p = m.groups()
                        dt = datetime(int(p[0]), int(p[1]), int(p[2]))
                    else:
                        p = m.groups()
                        month_abbr = p[1][:3].capitalize()
                        dt = datetime.strptime(f"{p[0]} {month_abbr} {p[2]}", "%d %b %Y")
                    
                    if 2000 <= dt.year <= 2040:
                        found_dates.append(dt)
                except Exception:
                    continue
        return found_dates
