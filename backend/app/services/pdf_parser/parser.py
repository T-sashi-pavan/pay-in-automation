import base64
import io
import json
import logging
import re
import os
import shutil

logger = logging.getLogger(__name__)
from datetime import date
from typing import List, Dict, Any, Optional, Tuple
import pdfplumber

from backend.app.services.excel_parser.parser import ExcelParserService, is_rule_effectively_empty, check_duplicate_slab_ranges
from backend.app.services.normalizer.normalizer import ValueNormalizer
from backend.app.services.validator.validator import RuleValidator

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
try:
    import pytesseract
    from pytesseract import Output
except ImportError:
    pytesseract = None
try:
    from PIL import Image
except ImportError:
    Image = None
try:
    import anthropic
except ImportError:
    anthropic = None
try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None
try:
    import openai
except ImportError:
    openai = None

if pytesseract is not None and shutil.which("tesseract") is None:
    _WINDOWS_TESSERACT_CANDIDATES = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for _candidate in _WINDOWS_TESSERACT_CANDIDATES:
        if _candidate and os.path.isfile(_candidate):
            pytesseract.pytesseract.tesseract_cmd = _candidate
            break

ANTHROPIC_VISION_MODEL = os.getenv("ANTHROPIC_VISION_MODEL", "claude-haiku-4-5-20251001")
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")

PDF_VISION_MAX_PAGES = int(os.getenv("PDF_VISION_MAX_PAGES", "60"))

LLM_EXTRACTION_PROMPT = """You are reading one page of an insurance commission circular.
This application only tracks the MOTOR DEPARTMENT (vehicle insurance) commission data. Ignore and completely skip any other departments (e.g., Health, Marine, Engineering, Fire, Life, Miscellaneous non-motor, etc.). If the page covers a non-motor department, return an empty rows list.

For motor department pages, convert natural language commission circular text and tables into structured CRM records.

====================================================
PRODUCT / CLASS / SUB CLASS MAPPING RULES
====================================================
- product: Extract the product name explicitly. Do NOT default to "ALL" if any of the following products are mentioned on the page or in the context/header:
  * Private Car
  * Two Wheeler (Scooter / Scooter only)
  * Two Wheeler (Bike / Bike only / Both bike and Scooters)
  * GCV (Goods Carrying Commercial Vehicle / GCCV)
  * PCV (Passenger Carrying Commercial Vehicle / PCCV)
  * Taxi (4 Wheeled PCCV carrying capacity <= 6 passengers)
  * Tractor (Agricultural Tractor)
  * Misc (Miscellaneous Class of Vehicle, Harvester, JCB, Harvester/Tractor, etc.)
  * E-Rickshaw / E-cart
- class: Extract class name if mentioned, otherwise "ALL".
- sub_class: Extract subclass/segment details (e.g. carrying capacity, seating capacity, GVW, engine capacity details, e.g. "GCV with GVW > 40000 Kg", "Both Bike and Scooters", "Private Car diesel", "Taxi", "PCV Bus school"). NEVER default to "ALL" if there are specific segments mentioned in the text.

====================================================
POLICY TYPE / PLAN TYPE MAPPING RULES
====================================================
- policy_type: Extract "Comprehensive" (Package/Package Policy), "Standalone Own Damage" (Standalone OD/SAOD/SOD), "Third Party" (TP/SATP/Liability only). Do not default to "ALL".
- plan_type: Extract "Package Policy", "Liability Only Policy", "Stand Alone Own Damage Policy", or duration designations (e.g., 1+1, 1+3, 3+3, 5+5). If terms like Package Policy or Stand Alone Own Damage are present in the table headers or rows, write them here. Do not default to "ALL".

====================================================
NCB & CPA STATUS MAPPING RULES
====================================================
- ncb: Extract the exact NCB condition from the text. Look for phrases like "without NCB", "NCB cases only", "with NCB", "Break in >90 days", etc. Do NOT default to "ALL" if there is an NCB condition.
- cpa: Extract the CPA condition if mentioned. Look for phrases like "with CPA", "without CPA", "Stand Alone CPA", "PA Owner Driver", etc. Do NOT default to "ALL" if mentioned.

====================================================
STATE, ZONE, AND RTO MAPPING RULES
====================================================
- state: Extract all state names or abbreviations (e.g. Kerala, Tamil Nadu, Karnataka, Assam, Madhya Pradesh, Uttarakhand/UK). If the circular lists specific states for a commission rate, extract them.
- zone: Extract the specific zone (North, South, East, West, Central, etc.) if mentioned.
- rto: Extract RTO codes or regions if mentioned (e.g. specific RTO codes, locations, or states specific zones).

====================================================
PREMIUM TYPE RULES
====================================================
- premium_type: Extract the premium type this rule applies to.
  * A row/rule containing only OD commission should have premium_type = "OD".
  * A row/rule containing TP commission should have premium_type = "TP".
  * A row/rule containing Net commission should have premium_type = "NET".
  * NEVER merge OD, TP, and NET into one row if they represent different rules or rates. If a rule specifies both OD and TP rates, split them into separate rules or slabs for each premium type!

====================================================
SLAB CLASSIFICATION REDESIGN & GROUPING
====================================================
A rule should NOT automatically become a slab simply because it contains multiple commission values.
We only create slab records when valid NUMERICAL slab ranges can actually be generated.

VALID SLAB CONDITIONS (Must be SLAB):
Only numeric thresholds where numerical ranges can be mapped to slab_from and slab_to (using float bounds or None for open limits) are SLABs.
Examples:
- Discount: "Discount up to 30%", "Discount >30% up to 60%", "Discount >60%" -> Slabs: 0-30, 31-60, 61-None.
- Vehicle Age: "Age=0" -> Slab: 0-0, "Age>=1" -> Slab: 1-None, "1-5 years" -> Slab: 1-5.
- CC: "<=1000 CC" -> Slab: 0-1000, "1001-1500 CC" -> Slab: 1001-1500, ">1500 CC" -> Slab: 1501-None.
- IDV: "0-5 lakh" -> Slab: 0-500000, "5-10 lakh" -> Slab: 500000-1000000.
- SI: "SI > 5 Lakh" -> Slab: 500001-None.
- GVW: "<=40000 kg" -> Slab: 0-40000, ">40000 kg" -> Slab: 40001-None.

INVALID SLAB CONDITIONS (Must remain NON_SLAB):
Do NOT create slabs for categorical conditions. They must remain NON_SLAB.
Examples:
- "With NCB" / "Without NCB" / "NCB Cases Only"
- "Good HP1" / "Good HP2"
- "Fleet" / "Non Fleet"
- "Partner Type", "Specific Dealer", "Manufacturer"
- "CPA YES" / "CPA NO"
- Remarks-based commission, Break-in cases, Renewal only, Roll Over only.
For these rules:
- Set commission_type = "NON_SLAB"
- Store the categorical condition in its matching CRM field (e.g. ncb field, cpa field, partner_type field, remarks, etc.).
- Never fabricate fake numeric ranges like 1-500000, 1-999999, 1-0, 0-MAX.

====================================================
SLAB GROUPING AND EXTRACTION RULES (CRITICAL)
====================================================
1. Group Tiers under One Rule: If a table, section, or paragraph lists multiple numeric ranges or tiers (such as discount bands, vehicle age bands, CC bands, weight bands) for the same product and subclass, they MUST be extracted as a SINGLE row in the 'rows' array with commission_type = "SLAB".
   * Place ALL the ranges/tiers in the 'slabs' array of this single row.
   * Do NOT create separate rows in the 'rows' list for each range/tier.
   * Example: If there are 3 discount ranges (up to 30%, 30-60%, >60%), they must be returned as 3 objects inside the 'slabs' array of ONE rule row, not 3 separate rows in the main 'rows' array.
   * If a page has multiple rows for the same subclass/product representing different ranges (e.g. "0 to 10 years" and "10 to 15 years" or "Discount of 60%" and "Discount exceeding 60%"), they MUST be grouped together into a SINGLE row with commission_type = "SLAB", containing all the slabs.

2. Slab Tiers Rate Mapping (CRITICAL):
   * Inside each object of the 'slabs' array, you MUST specify the correct, corresponding rate values for that SPECIFIC range/tier.
   * Do NOT copy the rule-level 'payin_od', 'payin_tp', or 'payin_net' values or keep them identical across all slab objects if the rates differ for each range in the text.
   * Set the outer rule-level rate fields ('payin_od', 'payin_tp', 'payin_net', 'payout_od', 'payout_tp', 'payout_net') to null when commission_type is SLAB. All rates must be defined inside each individual slab object in the 'slabs' array instead.
   * Example: If the text is:
     "Discount of 60%: Commission 5% on Net Premium (OD+TP). Discount exceeding 60%: Commission 2.5% on Net Premium (OD+TP)"
     Then you must return ONE row with commission_type = "SLAB" and slabs:
       - slab 1: slab_from = 0, slab_to = 60, payin_od = 5.0, payin_tp = 5.0, condition_field = "Discount"
       - slab 2: slab_from = 60, slab_to = "MAX", payin_od = 2.5, payin_tp = 2.5, condition_field = "Discount"
     (Note that Net Premium (OD+TP) means the percentage applies to both OD and TP, so populate both payin_od and payin_tp with that value!)
   * Example: If the text is:
     "Upto 10 years of vehicle age: 7.5% on OD + 2.5% on TP. Beyond 10 years upto 15 years: 5% on OD + 2.5% on TP"
     Then you must return ONE row with commission_type = "SLAB" and slabs:
       - slab 1: slab_from = 0, slab_to = 10, payin_od = 7.5, payin_tp = 2.5, condition_field = "Vehicle Age"
       - slab 2: slab_from = 10, slab_to = 15, payin_od = 5.0, payin_tp = 2.5, condition_field = "Vehicle Age"
   * Set condition_field to the field name (e.g. "Discount", "Vehicle Age", "CC").
   * Specify slab_from and slab_to clearly. For example, "up to 30%" -> slab_from = 0, slab_to = 30. ">30% up to 60%" -> slab_from = 30, slab_to = 60. ">60%" -> slab_from = 60, slab_to = "MAX".
   * Never output only a single tier rule if the table explicitly contains multiple tiers! Always extract every single range tier in the table.

====================================================
EXPLANATION PANEL & SOURCE
====================================================
- explanation: Every parsed row must contain a detailed explanation of why it was classified as SLAB or NON_SLAB.
  * If SLAB: Explain exactly why (e.g. "Reason: Detected numeric discount ranges. Original Text: [quote original text] -> Generated Slabs: 0-30, 31-60, 61-MAX").
  * If NON_SLAB: Explain why (e.g. "Stored as NON_SLAB. Reason: Commission depends on NCB status. No numeric slab boundaries exist. Mapped to NCB Status. Original Text: [quote original text]").
- source: Always preserve the COMPLETE original paragraph used for parsing. Never shorten or truncate it. Keep the full text so the user can easily trace and verify the rules.
- remarks: Capture any other footnotes, exclusions, or rules. Never discard remarks text.
"""

EXTRACTION_TOOL_SCHEMA = {
    "name": "extract_commission_rows",
    "description": "Record every commission-rule row read from this page.",
    "input_schema": {
        "type": "object",
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "lob": {"type": "string"},
                        "insurer": {"type": "string"},
                        "product": {"type": "string"},
                        "sub_product": {"type": "string"},
                        "policy_type": {"type": "string"},
                        "plan_type": {"type": "string"},
                        "file_type": {"type": "string"},
                        "class": {"type": "string"},
                        "sub_class": {"type": "string"},
                        "make": {"type": "string"},
                        "model": {"type": "string"},
                        "fuel_type": {"type": "string"},
                        "cpa": {"type": "string"},
                        "ncb": {"type": "string"},
                        "vehicle_age": {"type": "string"},
                        "partner_type": {"type": "string"},
                        "state": {"type": "string"},
                        "zone": {"type": "string"},
                        "rto": {"type": "string"},
                        "source": {"type": "string"},
                        "remarks": {"type": "string"},
                        "commission_type": {"type": "string", "enum": ["SLAB", "NON_SLAB"]},
                        "premium_type": {"type": "string", "enum": ["OD", "TP", "NET"]},
                        "payin_od": {"type": ["number", "null"]},
                        "payin_tp": {"type": ["number", "null"]},
                        "payin_net": {"type": ["number", "null"]},
                        "payout_od": {"type": ["number", "null"]},
                        "payout_tp": {"type": ["number", "null"]},
                        "payout_net": {"type": ["number", "null"]},
                        "payin_reward": {"type": ["number", "null"]},
                        "payout_reward": {"type": ["number", "null"]},
                        "payin_scheme": {"type": ["number", "null"]},
                        "payout_scheme": {"type": ["number", "null"]},
                        "explanation": {"type": "string"},
                        "slabs": {
                            "type": ["array", "null"],
                            "items": {
                                "type": "object",
                                "properties": {
                                    "payin_type": {"type": "string"},
                                    "premium_type": {"type": "string", "enum": ["OD", "TP", "NET"]},
                                    "slab_from": {"type": ["string", "number", "null"]},
                                    "slab_to": {"type": ["string", "number", "null"]},
                                    "payin_od": {"type": ["number", "null"]},
                                    "payin_tp": {"type": ["number", "null"]},
                                    "payin_net": {"type": ["number", "null"]},
                                    "payout_od": {"type": ["number", "null"]},
                                    "payout_tp": {"type": ["number", "null"]},
                                    "payout_net": {"type": ["number", "null"]},
                                    "condition_field": {"type": ["string", "null"]},
                                    "operator": {"type": ["string", "null"]},
                                    "value": {"type": ["number", "null"]},
                                    "original_text": {"type": ["string", "null"]}
                                }
                            }
                        }
                    },
                    "required": ["lob", "commission_type"]
                }
            }
        },
        "required": ["rows"]
    }
}

if genai_types is not None:
    _GEMINI_SLAB_SCHEMA = genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "payin_type": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "premium_type": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "slab_from": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "slab_to": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "payin_od": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payin_tp": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payin_net": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payout_od": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payout_tp": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payout_net": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "condition_field": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "operator": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "value": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "original_text": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
        }
    )
    _GEMINI_ROW_SCHEMA = genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "lob": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "insurer": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "product": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "sub_product": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "policy_type": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "plan_type": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "file_type": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "class": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "sub_class": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "make": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "model": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "fuel_type": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "cpa": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "ncb": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "vehicle_age": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "partner_type": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "state": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "zone": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "rto": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "source": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "remarks": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "commission_type": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "premium_type": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "payin_od": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payin_tp": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payin_net": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payout_od": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payout_tp": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payout_net": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payin_reward": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payout_reward": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payin_scheme": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "payout_scheme": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "explanation": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "slabs": genai_types.Schema(type=genai_types.Type.ARRAY, items=_GEMINI_SLAB_SCHEMA, nullable=True),
        }
    )
    GEMINI_RESPONSE_SCHEMA = genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={"rows": genai_types.Schema(type=genai_types.Type.ARRAY, items=_GEMINI_ROW_SCHEMA)},
        required=["rows"]
    )
else:
    GEMINI_RESPONSE_SCHEMA = None

_OPENAI_SLAB_SCHEMA = {
    "type": "object",
    "properties": {
        "payin_type": {"type": ["string", "null"]},
        "premium_type": {"type": ["string", "null"]},
        "slab_from": {"type": ["string", "number", "null"]},
        "slab_to": {"type": ["string", "number", "null"]},
        "payin_od": {"type": ["number", "null"]},
        "payin_tp": {"type": ["number", "null"]},
        "payin_net": {"type": ["number", "null"]},
        "payout_od": {"type": ["number", "null"]},
        "payout_tp": {"type": ["number", "null"]},
        "payout_net": {"type": ["number", "null"]},
        "condition_field": {"type": ["string", "null"]},
        "operator": {"type": ["string", "null"]},
        "value": {"type": ["number", "null"]},
        "original_text": {"type": ["string", "null"]}
    },
    "required": [
        "payin_type", "premium_type", "slab_from", "slab_to", "payin_od", "payin_tp", "payin_net",
        "payout_od", "payout_tp", "payout_net", "condition_field", "operator", "value", "original_text"
    ],
    "additionalProperties": False
}

_OPENAI_ROW_SCHEMA = {
    "type": "object",
    "properties": {
        "lob": {"type": ["string", "null"]},
        "insurer": {"type": ["string", "null"]},
        "product": {"type": ["string", "null"]},
        "sub_product": {"type": ["string", "null"]},
        "policy_type": {"type": ["string", "null"]},
        "plan_type": {"type": ["string", "null"]},
        "file_type": {"type": ["string", "null"]},
        "class": {"type": ["string", "null"]},
        "sub_class": {"type": ["string", "null"]},
        "make": {"type": ["string", "null"]},
        "model": {"type": ["string", "null"]},
        "fuel_type": {"type": ["string", "null"]},
        "cpa": {"type": ["string", "null"]},
        "ncb": {"type": ["string", "null"]},
        "vehicle_age": {"type": ["string", "null"]},
        "partner_type": {"type": ["string", "null"]},
        "state": {"type": ["string", "null"]},
        "zone": {"type": ["string", "null"]},
        "rto": {"type": ["string", "null"]},
        "source": {"type": ["string", "null"]},
        "remarks": {"type": ["string", "null"]},
        "commission_type": {"type": ["string", "null"]},
        "premium_type": {"type": ["string", "null"]},
        "payin_od": {"type": ["number", "null"]},
        "payin_tp": {"type": ["number", "null"]},
        "payin_net": {"type": ["number", "null"]},
        "payout_od": {"type": ["number", "null"]},
        "payout_tp": {"type": ["number", "null"]},
        "payout_net": {"type": ["number", "null"]},
        "payin_reward": {"type": ["number", "null"]},
        "payout_reward": {"type": ["number", "null"]},
        "payin_scheme": {"type": ["number", "null"]},
        "payout_scheme": {"type": ["number", "null"]},
        "explanation": {"type": ["string", "null"]},
        "slabs": {"type": ["array", "null"], "items": _OPENAI_SLAB_SCHEMA}
    },
    "required": [
        "lob", "insurer", "product", "sub_product", "policy_type", "plan_type", "file_type",
        "class", "sub_class", "make", "model", "fuel_type", "cpa", "ncb", "vehicle_age",
        "partner_type", "state", "zone", "rto", "source", "remarks", "commission_type",
        "premium_type", "payin_od", "payin_tp", "payin_net", "payout_od", "payout_tp", "payout_net",
        "payin_reward", "payout_reward", "payin_scheme", "payout_scheme", "explanation", "slabs"
    ],
    "additionalProperties": False
}

OPENAI_RESPONSE_SCHEMA = {
    "name": "extract_commission_rows",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {"rows": {"type": "array", "items": _OPENAI_ROW_SCHEMA}},
        "required": ["rows"],
        "additionalProperties": False,
    },
}


class PdfParserService:
    """
    Parses commission-grid tables out of a PDF using LLM.
    """

    def __init__(self):
        self.excel_parser = ExcelParserService()
        self.normalizer = ValueNormalizer()

    def parse_pdf(self, file_bytes: bytes, filename: Optional[str] = None) -> List[Dict[str, Any]]:
        company = "Unknown"
        if filename:
            fn_lower = filename.lower()
            if "tata" in fn_lower:
                company = "Tata"
            elif "shriram" in fn_lower:
                company = "Shriram"
            elif "chola" in fn_lower:
                company = "Cholamandalam"
            elif "digit" in fn_lower:
                company = "Digit"
            elif "oriental" in fn_lower:
                company = "Oriental"

        all_parsed_rules: List[Dict[str, Any]] = []
        existing_keys: set = set()
        usage = {
            "provider": None,
            "pages_sent": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "pages_capped": 0,
            "errors": 0,
            "remaining_tokens": "N/A",
            "remaining_requests": "N/A",
            "limit_tokens": "N/A",
            "limit_requests": "N/A"
        }

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"[PDF START] Parsing '{filename}' - Total pages: {total_pages}")

            for page_idx, page in enumerate(pdf.pages):
                page_num = page_idx + 1
                text = page.extract_text() or ""

                if usage["pages_sent"] >= PDF_VISION_MAX_PAGES:
                    usage["pages_capped"] += 1
                    logger.warning(f"  [COST GUARD] Page {page_num} skipped — reached PDF_VISION_MAX_PAGES={PDF_VISION_MAX_PAGES} limit.")
                    continue

                count = -1
                if text.strip():
                    logger.info(f"  [PAGE START] Page {page_num}/{total_pages} - Analyzing text content...")
                    count = self._llm_text_extract_page(
                        text, page_idx, filename, company, existing_keys, all_parsed_rules, usage
                    )
                    if count >= 0:
                        logger.info(f"  [PAGE COMPLETED] Page {page_num}/{total_pages} - Extracted {count} rules via text LLM.")
                        continue

                logger.info(f"  [PAGE START] Page {page_num}/{total_pages} - Analyzing scanned/image content via Vision...")
                count = self._llm_vision_extract_page(
                    file_bytes, page_idx, filename, company, existing_keys, all_parsed_rules, usage
                )
                if count >= 0:
                    logger.info(f"  [PAGE COMPLETED] Page {page_num}/{total_pages} - Extracted {count} rules via vision LLM.")
                else:
                    ocr_table = self._ocr_page_table(file_bytes, page_idx)
                    if not ocr_table or len(ocr_table) < 2:
                        logger.warning(f"  [PAGE SKIP] Page {page_num}/{total_pages} - Scanned page, OCR could not reconstruct tables.")
                        continue
                    headers, data_rows = ocr_table[0], ocr_table[1:]
                    sheet_name = f"Page {page_num} (OCR)"
                    count = self.excel_parser.parse_table(
                        headers, data_rows, sheet_name, filename, company, existing_keys, all_parsed_rules
                    )
                    logger.info(f"  [PAGE COMPLETED] Page {page_num}/{total_pages} - Extracted {count} rules from '{sheet_name}' via OCR.")

        # Perform PDF-specific grouping to merge slabs split across different rows/bullets
        all_parsed_rules = self._group_and_merge_pdf_rules(all_parsed_rules)

        final_rules = self.excel_parser._group_and_merge_rules(all_parsed_rules)
        before = len(final_rules)
        final_rules = [r for r in final_rules if not is_rule_effectively_empty(r) and not self._is_rule_empty_of_rates(r)]
        dropped = before - len(final_rules)
        if dropped:
            logger.info(f"  [DATA QUALITY] Dropped {dropped} empty/invalid rule(s) from parsed output.")

        if usage["pages_sent"] > 0:
            logger.info(
                f"\n[LLM SUMMARY] provider={usage['provider']} | pages_sent={usage['pages_sent']} | errors={usage['errors']}\n"
                f"  Cumulative Token Usage: input_tokens={usage['input_tokens']:,} | output_tokens={usage['output_tokens']:,} | total_tokens={usage['total_tokens']:,}\n"
                f"  Rate Limit Status: remaining_tokens={usage['remaining_tokens']} | remaining_requests={usage['remaining_requests']} | limit_tokens={usage['limit_tokens']} | limit_requests={usage['limit_requests']}\n"
            )

        logger.info(f"[PDF COMPLETED] Successfully parsed {filename}. Grouped {len(all_parsed_rules)} rules into {len(final_rules)} merged rules.")
        return final_rules

    def _is_empty_rate(self, val: Any) -> bool:
        if val is None:
            return True
        val_str = str(val).strip().upper()
        if val_str in ("", "NONE", "NULL", "NIL", "0", "0.0", "0%", "N/A", "NA"):
            return True
        try:
            clean_val = val_str.replace("%", "").strip()
            if float(clean_val) == 0.0:
                return True
        except ValueError:
            pass
        return False

    def _is_rule_empty_of_rates(self, rule: Dict[str, Any]) -> bool:
        rate_fields = ("payin_od", "payin_tp", "payin_net", "payin_reward", "payin_scheme")
        if not all(self._is_empty_rate(rule.get(f)) for f in rate_fields):
            return False
            
        for slab in rule.get("slabs") or []:
            if not all(self._is_empty_rate(slab.get(f)) for f in ("payin_od", "payin_tp", "payin_net")):
                return False
                
        return True

    def _group_and_merge_pdf_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not rules:
            return []
            
        grouped: Dict[Tuple, List[Dict[str, Any]]] = {}
        for r in rules:
            key = (
                str(r.get("lob") or "").strip().upper(),
                str(r.get("file_type") or "").strip().upper(),
                str(r.get("insurance_company") or "").strip().upper(),
                str(r.get("product") or "").strip().upper(),
                str(r.get("policy_type") or "").strip().upper(),
                str(r.get("plan_type") or "").strip().upper(),
                str(r.get("sub_product") or "").strip().upper(),
                str(r.get("class") or "").strip().upper(),
                str(r.get("class_") or "").strip().upper(),
                str(r.get("sub_class") or "").strip().upper(),
                str(r.get("make") or "").strip().upper(),
                str(r.get("model") or "").strip().upper(),
                str(r.get("fuel_type") or "").strip().upper(),
                str(r.get("body_type") or "").strip().upper(),
                str(r.get("vehicle_age_from") or "").strip(),
                str(r.get("vehicle_age_to") or "").strip(),
                str(r.get("cpa_status") or "").strip().upper(),
                str(r.get("ncb_status") or "").strip().upper(),
                str(r.get("partner_type") or "").strip().upper(),
                str(r.get("state") or "").strip().upper(),
                str(r.get("zone") or "").strip().upper(),
                str(r.get("rto") or "").strip().upper(),
            )
            grouped.setdefault(key, []).append(r)
            
        merged_rules = []
        for key, group in grouped.items():
            if len(group) == 1:
                merged_rules.append(group[0])
                continue
                
            any_slab = any(r.get("commission_type") == "SLAB" for r in group)
            
            merged_rule = group[0].copy()
            
            if any_slab:
                merged_rule["commission_type"] = "SLAB"
                merged_rule["slab_configuration"] = True
                
                # Reset direct rates
                for f in ("payin_od", "payout_od", "payin_tp", "payout_tp", "payin_net", "payout_net",
                          "payin_reward", "payout_reward", "payin_scheme", "payout_scheme"):
                    merged_rule[f] = None
                    
                combined_slabs = []
                seen_slab_keys = set()
                
                for r in group:
                    slabs_to_add = r.get("slabs") or []
                    if r.get("commission_type") == "NON_SLAB":
                        rate_buckets = (
                            ("OD", "payin_od", r.get("payin_od"), r.get("payout_od")),
                            ("TP", "payin_tp", r.get("payin_tp"), r.get("payout_tp")),
                            ("NET", "payin_net", r.get("payin_net"), r.get("payout_net")),
                        )
                        for premium_type, payin_field, payin_val, payout_val in rate_buckets:
                            if payin_val is not None:
                                combined_slabs.append({
                                    "payin_type": "PERCENTAGE",
                                    "premium_type": premium_type,
                                    "slab_from": None,
                                    "slab_to": None,
                                    "payin_od": payin_val if premium_type == "OD" else None,
                                    "payout_od": payout_val if premium_type == "OD" else None,
                                    "payin_tp": payin_val if premium_type == "TP" else None,
                                    "payout_tp": payout_val if premium_type == "TP" else None,
                                    "payin_net": payin_val if premium_type == "NET" else None,
                                    "payout_net": payout_val if premium_type == "NET" else None,
                                    "condition_field": None,
                                    "operator": None,
                                    "value": None,
                                    "original_text": r.get("source")
                                })
                    else:
                        for s in slabs_to_add:
                            s_key = (
                                s.get("premium_type"),
                                s.get("slab_from"),
                                s.get("slab_to"),
                                s.get("payin_od"),
                                s.get("payin_tp"),
                                s.get("payin_net")
                            )
                            if s_key not in seen_slab_keys:
                                seen_slab_keys.add(s_key)
                                combined_slabs.append(s)
                                
                merged_rule["slabs"] = combined_slabs
                
                # Re-check duplicate slab ranges
                dup_warnings = check_duplicate_slab_ranges(merged_rule["slabs"])
                merged_rule["warnings"] = [w for w in merged_rule.get("warnings") or [] if not w.startswith("Slab range warning:")]
                if dup_warnings:
                    merged_rule["warnings"] = list(merged_rule["warnings"]) + dup_warnings
                    merged_rule["validation_status"] = "WARNING"
            else:
                for r in group[1:]:
                    if merged_rule["payin_od"] is None: merged_rule["payin_od"] = r.get("payin_od")
                    if merged_rule["payin_tp"] is None: merged_rule["payin_tp"] = r.get("payin_tp")
                    if merged_rule["payin_net"] is None: merged_rule["payin_net"] = r.get("payin_net")
                    if merged_rule["payout_od"] is None: merged_rule["payout_od"] = r.get("payout_od")
                    if merged_rule["payout_tp"] is None: merged_rule["payout_tp"] = r.get("payout_tp")
                    if merged_rule["payout_net"] is None: merged_rule["payout_net"] = r.get("payout_net")
                    
                for prem in ("od", "tp", "net"):
                    payin_f = f"payin_{prem}"
                    payout_f = f"payout_{prem}"
                    if merged_rule[payout_f] is None and merged_rule[payin_f] is not None:
                        merged_rule[payout_f] = round(float(merged_rule[payin_f]) * 0.8, 6)

            sources = []
            remarks_list = []
            warnings_list = list(merged_rule.get("warnings") or [])
            
            for r in group:
                if r.get("source") and r.get("source") not in sources:
                    sources.append(r["source"])
                if r.get("remarks") and r.get("remarks") != "ALL" and r.get("remarks") not in remarks_list:
                    remarks_list.append(r["remarks"])
                for w in r.get("warnings") or []:
                    if w not in warnings_list:
                        warnings_list.append(w)
                        
            merged_rule["source"] = " | ".join(sources)
            merged_rule["remarks"] = "; ".join(remarks_list) if remarks_list else "ALL"
            merged_rule["warnings"] = warnings_list
            
            merged_rules.append(merged_rule)
            
        return merged_rules

    def _render_page_png(self, file_bytes: bytes, page_idx: int) -> Optional[bytes]:
        if fitz is None:
            return None
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pix = doc[page_idx].get_pixmap(matrix=fitz.Matrix(2, 2))
            return pix.tobytes("png")
        except Exception as e:
            logger.error(f"  [LLM VISION ERROR] Page {page_idx + 1} render failed: {e}")
            return None

    def _llm_text_extract_page(
        self, text_content: str, page_idx: int, filename: Optional[str], company: str,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]], usage: Dict[str, Any]
    ) -> int:
        if anthropic is not None and os.getenv("ANTHROPIC_API_KEY"):
            return self._anthropic_text_extract_page(text_content, page_idx, filename, company, existing_keys, all_parsed_rules, usage)

        if openai is not None and os.getenv("OPENAI_API_KEY"):
            return self._openai_text_extract_page(text_content, page_idx, filename, company, existing_keys, all_parsed_rules, usage)

        if genai is not None and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            return self._gemini_text_extract_page(text_content, page_idx, filename, company, existing_keys, all_parsed_rules, usage)

        return -1

    def _llm_vision_extract_page(
        self, file_bytes: bytes, page_idx: int, filename: Optional[str], company: str,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]], usage: Dict[str, Any]
    ) -> int:
        if anthropic is not None and os.getenv("ANTHROPIC_API_KEY"):
            return self._anthropic_vision_extract_page(file_bytes, page_idx, filename, company, existing_keys, all_parsed_rules, usage)

        if openai is not None and os.getenv("OPENAI_API_KEY"):
            return self._openai_vision_extract_page(file_bytes, page_idx, filename, company, existing_keys, all_parsed_rules, usage)

        if genai is not None and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            return self._gemini_vision_extract_page(file_bytes, page_idx, filename, company, existing_keys, all_parsed_rules, usage)

        return -1

    def _anthropic_vision_extract_page(
        self, file_bytes: bytes, page_idx: int, filename: Optional[str], company: str,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]], usage: Dict[str, Any]
    ) -> int:
        png_bytes = self._render_page_png(file_bytes, page_idx)
        if png_bytes is None:
            return -1
        try:
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model=ANTHROPIC_VISION_MODEL,
                max_tokens=8192,
                tools=[EXTRACTION_TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": "extract_commission_rows"},
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(png_bytes).decode("utf-8")}},
                        {"type": "text", "text": LLM_EXTRACTION_PROMPT},
                    ],
                }],
            )
            self._record_usage(usage, "anthropic", page_idx + 1, response.usage.input_tokens, response.usage.output_tokens)
            tool_use = next((b for b in response.content if b.type == "tool_use"), None)
            if tool_use is None:
                return 0
            rows = tool_use.input.get("rows", [])
        except Exception as e:
            usage["errors"] += 1
            logger.error(f"  [LLM VISION ERROR] Page {page_idx + 1} (Claude): {e}")
            return -1
        return self._append_llm_rows(rows, company, filename, page_idx + 1, existing_keys, all_parsed_rules)

    def _anthropic_text_extract_page(
        self, text_content: str, page_idx: int, filename: Optional[str], company: str,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]], usage: Dict[str, Any]
    ) -> int:
        try:
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            response = client.messages.create(
                model=ANTHROPIC_VISION_MODEL,
                max_tokens=8192,
                tools=[EXTRACTION_TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": "extract_commission_rows"},
                messages=[{
                    "role": "user",
                    "content": f"{LLM_EXTRACTION_PROMPT}\n\nHere is the raw text extracted from page {page_idx + 1}:\n{text_content}",
                }],
            )
            self._record_usage(usage, "anthropic", page_idx + 1, response.usage.input_tokens, response.usage.output_tokens)
            tool_use = next((b for b in response.content if b.type == "tool_use"), None)
            if tool_use is None:
                return 0
            rows = tool_use.input.get("rows", [])
        except Exception as e:
            usage["errors"] += 1
            logger.error(f"  [LLM TEXT ERROR] Page {page_idx + 1} (Claude): {e}")
            return -1
        return self._append_llm_rows(rows, company, filename, page_idx + 1, existing_keys, all_parsed_rules)

    def _openai_vision_extract_page(
        self, file_bytes: bytes, page_idx: int, filename: Optional[str], company: str,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]], usage: Dict[str, Any]
    ) -> int:
        png_bytes = self._render_page_png(file_bytes, page_idx)
        if png_bytes is None:
            return -1
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            raw_response = client.with_raw_response.chat.completions.create(
                model=OPENAI_VISION_MODEL,
                max_tokens=8192,
                response_format={"type": "json_schema", "json_schema": OPENAI_RESPONSE_SCHEMA},
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": LLM_EXTRACTION_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(png_bytes).decode('utf-8')}"}},
                    ],
                }],
            )
            headers = raw_response.headers
            response = raw_response.parse()
            
            # Record rate limits
            self._update_openai_rate_limits(usage, headers)
            
            self._record_usage(usage, "openai", page_idx + 1, response.usage.prompt_tokens, response.usage.completion_tokens)
            content = response.choices[0].message.content
            data = json.loads(content) if content else {}
            rows = data.get("rows", [])
        except Exception as e:
            usage["errors"] += 1
            logger.error(f"  [LLM VISION ERROR] Page {page_idx + 1} (OpenAI): {e}")
            return -1
        return self._append_llm_rows(rows, company, filename, page_idx + 1, existing_keys, all_parsed_rules)

    def _openai_text_extract_page(
        self, text_content: str, page_idx: int, filename: Optional[str], company: str,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]], usage: Dict[str, Any]
    ) -> int:
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            raw_response = client.with_raw_response.chat.completions.create(
                model=OPENAI_VISION_MODEL,
                max_tokens=8192,
                response_format={"type": "json_schema", "json_schema": OPENAI_RESPONSE_SCHEMA},
                messages=[{
                    "role": "user",
                    "content": f"{LLM_EXTRACTION_PROMPT}\n\nHere is the raw text extracted from page {page_idx + 1}:\n{text_content}",
                }],
            )
            headers = raw_response.headers
            response = raw_response.parse()
            
            # Record rate limits
            self._update_openai_rate_limits(usage, headers)
            
            self._record_usage(usage, "openai", page_idx + 1, response.usage.prompt_tokens, response.usage.completion_tokens)
            content = response.choices[0].message.content
            data = json.loads(content) if content else {}
            rows = data.get("rows", [])
        except Exception as e:
            usage["errors"] += 1
            logger.error(f"  [LLM TEXT ERROR] Page {page_idx + 1} (OpenAI): {e}")
            return -1
        return self._append_llm_rows(rows, company, filename, page_idx + 1, existing_keys, all_parsed_rules)

    def _update_openai_rate_limits(self, usage: Dict[str, Any], headers) -> None:
        usage["remaining_tokens"] = headers.get("x-ratelimit-remaining-tokens", "N/A")
        usage["remaining_requests"] = headers.get("x-ratelimit-remaining-requests", "N/A")
        usage["limit_tokens"] = headers.get("x-ratelimit-limit-tokens", "N/A")
        usage["limit_requests"] = headers.get("x-ratelimit-limit-requests", "N/A")

    def _gemini_vision_extract_page(
        self, file_bytes: bytes, page_idx: int, filename: Optional[str], company: str,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]], usage: Dict[str, Any]
    ) -> int:
        png_bytes = self._render_page_png(file_bytes, page_idx)
        if png_bytes is None:
            return -1
        try:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=GEMINI_VISION_MODEL,
                contents=[
                    genai_types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
                    LLM_EXTRACTION_PROMPT,
                ],
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GEMINI_RESPONSE_SCHEMA,
                ),
            )
            um = response.usage_metadata
            self._record_usage(usage, "gemini", page_idx + 1, um.prompt_token_count or 0, um.candidates_token_count or 0)
            data = json.loads(response.text)
            rows = data.get("rows", [])
        except Exception as e:
            usage["errors"] += 1
            logger.error(f"  [LLM VISION ERROR] Page {page_idx + 1} (Gemini): {e}")
            return -1
        return self._append_llm_rows(rows, company, filename, page_idx + 1, existing_keys, all_parsed_rules)

    def _gemini_text_extract_page(
        self, text_content: str, page_idx: int, filename: Optional[str], company: str,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]], usage: Dict[str, Any]
    ) -> int:
        try:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=GEMINI_VISION_MODEL,
                contents=[
                    f"{LLM_EXTRACTION_PROMPT}\n\nHere is the raw text extracted from page {page_idx + 1}:\n{text_content}"
                ],
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GEMINI_RESPONSE_SCHEMA,
                ),
            )
            um = response.usage_metadata
            self._record_usage(usage, "gemini", page_idx + 1, um.prompt_token_count or 0, um.candidates_token_count or 0)
            data = json.loads(response.text)
            rows = data.get("rows", [])
        except Exception as e:
            usage["errors"] += 1
            logger.error(f"  [LLM TEXT ERROR] Page {page_idx + 1} (Gemini): {e}")
            return -1
        return self._append_llm_rows(rows, company, filename, page_idx + 1, existing_keys, all_parsed_rules)

    def _record_usage(self, usage: Dict[str, Any], provider: str, page_num: int, input_tokens: int, output_tokens: int) -> None:
        usage["provider"] = provider
        usage["pages_sent"] += 1
        usage["input_tokens"] += input_tokens
        usage["output_tokens"] += output_tokens
        usage["total_tokens"] += input_tokens + output_tokens
        logger.info(f"  [LLM USAGE] Page {page_num} ({provider}): input={input_tokens:,} output={output_tokens:,} tokens")

    def _append_llm_rows(
        self, rows: List[Dict[str, Any]], company: str, filename: Optional[str], page_num: int,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]]
    ) -> int:
        count = 0
        slabs_count = 0
        non_slabs_count = 0
        for row in rows:
            rule_dict = self._llm_row_to_rule(row, company, filename, page_num, existing_keys)
            if rule_dict:
                all_parsed_rules.append(rule_dict)
                count += 1
                if rule_dict.get("commission_type") == "SLAB":
                    slabs_count += 1
                else:
                    non_slabs_count += 1
        
        logger.info(
            f"  [PAGE RESULTS] Page {page_num}: LLM returned {len(rows)} raw rows. "
            f"Parsed {count} motor rules ({slabs_count} SLAB, {non_slabs_count} NON_SLAB)."
        )
        return count

    def _llm_row_to_rule(
        self, row: Dict[str, Any], company: str, filename: Optional[str], page_num: int, existing_keys: set
    ) -> Optional[Dict[str, Any]]:
        """Converts one LLM-extracted row into the same rule-dict shape the Excel/Word parsers emit."""
        
        # Verify LOB
        lob = row.get("lob")
        if lob and str(lob).strip().lower() != "motor":
            # Skip non-Motor rules
            return None

        # Resolve field values
        insurer_name = row.get("insurer") or company
        product = row.get("product") or "ALL"
        sub_product = row.get("sub_product") or "NA"
        policy_type = row.get("policy_type") or "ALL"
        plan_type = row.get("plan_type") or "ALL"
        file_type = row.get("file_type") or "ALL"
        class_val = row.get("class") or "ALL"
        sub_class = row.get("sub_class") or "ALL"
        make = row.get("make") or "ALL"
        model = row.get("model") or "ALL"
        fuel_type = row.get("fuel_type") or "ALL"
        cpa = row.get("cpa") or "ALL"
        ncb = row.get("ncb") or "ALL"
        zone = row.get("zone") or "ALL"
        rto = row.get("rto") or "ALL"
        source = row.get("source") or "ALL"
        remarks = row.get("remarks") or ""

        # Perform advanced text-based inferences to augment LLM extractions
        source_text = str(source)
        remarks_text = str(remarks)
        explanation_text = str(row.get("explanation") or "")
        combined_text = f"{source_text} {remarks_text} {explanation_text}".lower()

        # 1. Product & Sub Class Inferences
        if product == "ALL" or not product:
            if "private car" in combined_text or "pvt car" in combined_text:
                product = "Private Car"
            elif any(kw in combined_text for kw in ["two wheeler", "2w", "bike", "scooter", "motor cycle", "moped", "scooty"]):
                product = "Two Wheeler"
            elif "taxi" in combined_text:
                product = "Taxi"
            elif "tractor" in combined_text:
                product = "Tractor"
            elif "gcv" in combined_text or "goods carrying" in combined_text:
                product = "GCV"
            elif "pcv" in combined_text or "passenger carrying" in combined_text:
                product = "PCV"
            elif any(kw in combined_text for kw in ["misc-d", "misc d", "miscellaneous"]):
                product = "Misc D"
            elif "e-rickshaw" in combined_text or "e-cart" in combined_text:
                product = "E-Rickshaw"

        if sub_class == "ALL" or not sub_class:
            if product == "Two Wheeler":
                if "scooter" in combined_text or "scooty" in combined_text or "moped" in combined_text:
                    sub_class = "Two Wheeler (Scooters)"
                elif "bike" in combined_text or "motorcycle" in combined_text or "motor cycle" in combined_text:
                    sub_class = "Two Wheeler (Bike)"
                else:
                    sub_class = "Two Wheeler (Both bike and Scooters)"
            elif product == "GCV":
                gvw_match = re.search(r"gvw\s*(?:>|<=|>=|<)?\s*\d+", combined_text)
                if gvw_match:
                    sub_class = f"GCV {gvw_match.group(0).upper()}"
                else:
                    sub_class = "GCV"
            elif product == "PCV":
                if "bus" in combined_text:
                    sub_class = "PCV Bus"
                elif "taxi" in combined_text:
                    sub_class = "Taxi"
                else:
                    sub_class = "PCV"
            elif "both bike and scooters" in combined_text:
                sub_class = "Two Wheeler (Both bike and Scooters)"
            elif "private car" in combined_text:
                sub_class = "Private Car"
            elif "taxi" in combined_text:
                sub_class = "Taxi"

        # 2. Policy Type & Plan Type Inferences
        combined_policy_text = f"{policy_type} {plan_type} {combined_text}".lower()
        if any(kw in combined_policy_text for kw in ["saod", "standalone od", "sod", "standalone own damage", "stand alone", "stand alone own damage"]):
            policy_type = "Standalone Own Damage"
            plan_type = "Stand Alone Own Damage Policy"
        elif any(kw in combined_policy_text for kw in ["satp", "third party", "tp only", "act only", "tp policy", "tp cases", "liability only", "liability"]):
            policy_type = "Third Party"
            plan_type = "Liability Only Policy"
        elif any(kw in combined_policy_text for kw in ["package", "comprehensive", "p & l", "pkg"]):
            policy_type = "Comprehensive"
            plan_type = "Package Policy"

        # 3. NCB Status Inference
        if ncb == "ALL" or not ncb:
            if "without ncb" in combined_text or "no ncb" in combined_text:
                ncb = "without NCB"
            elif "ncb cases only" in combined_text or "only ncb" in combined_text:
                ncb = "NCB cases only"
            elif "with ncb" in combined_text or "has ncb" in combined_text:
                ncb = "with NCB"
            elif any(kw in combined_text for kw in ["break in >90", "break-in > 90", "break-in >90"]):
                ncb = "Break in >90 days"
            elif "break in" in combined_text or "break-in" in combined_text:
                ncb = "Break-in"

        # 4. CPA Status Inference
        if cpa == "ALL" or not cpa:
            if "without cpa" in combined_text or "excluding cpa" in combined_text:
                cpa = "without CPA"
            elif "with cpa" in combined_text or "including cpa" in combined_text or "cpa cover" in combined_text or "pa owner driver" in combined_text or "cpa yes" in combined_text:
                cpa = "with CPA"
            elif "stand alone cpa" in combined_text or "sacpa" in combined_text:
                cpa = "Stand Alone CPA"

        state_raw = row.get("state")
        normalized_state = self.normalizer.normalize_states(state_raw) if state_raw else None

        # Resolve vehicle age ranges
        age_from, age_to = self.normalizer.normalize_vehicle_age(row.get("vehicle_age"))

        # Payins
        payin_od = row.get("payin_od")
        payin_tp = row.get("payin_tp")
        payin_net = row.get("payin_net")
        payin_reward = row.get("payin_reward")
        payin_scheme = row.get("payin_scheme")

        # Payouts
        payout_od = row.get("payout_od")
        payout_tp = row.get("payout_tp")
        payout_net = row.get("payout_net")
        payout_reward = row.get("payout_reward")
        payout_scheme = row.get("payout_scheme")

        # Default payouts to 80% of payin if missing
        if payout_od is None and payin_od is not None:
            payout_od = round(payin_od * 0.8, 6)
        if payout_tp is None and payin_tp is not None:
            payout_tp = round(payin_tp * 0.8, 6)
        if payout_net is None and payin_net is not None:
            payout_net = round(payin_net * 0.8, 6)
        if payout_reward is None and payin_reward is not None:
            payout_reward = round(payin_reward * 0.8, 6)
        if payout_scheme is None and payin_scheme is not None:
            payout_scheme = round(payin_scheme * 0.8, 6)

        rule_data: Dict[str, Any] = {
            "sheet_name": f"Page {page_num} (LLM)",
            "lob": "Motor",
            "file_type": file_type,
            "insurance_company": insurer_name,
            "product": product,
            "policy_type": policy_type,
            "plan_type": plan_type,
            "sub_product": sub_product,
            "class_": class_val,
            "sub_class": sub_class,
            "make": make,
            "model": model,
            "fuel_type": fuel_type,
            "body_type": "ALL",
            "vehicle_age_from": age_from,
            "vehicle_age_to": age_to,
            "cpa_status": cpa,
            "ncb_status": ncb,
            "partner_type": row.get("partner_type") or "All Partners",
            "state": normalized_state,
            "zone": zone,
            "source": source,
            "rto": rto,
            "effective_date": date.today(),
            "remarks": remarks or "ALL",
        }

        # Validate
        status, warnings = RuleValidator.validate_rule(rule_data, existing_keys)

        # Handle slabs validation and classification redesign
        is_slab = (row.get("commission_type") == "SLAB")
        slabs_in = row.get("slabs") or []

        # Slabs validation: Whitelist of allowed numeric fields
        allowed_numeric_fields = {
            "DISCOUNT", "VEHICLE AGE", "AGE", "IDV", "SUM INSURED", "SI", "CC", "GVW", 
            "WEIGHT", "ENGINE CAPACITY", "GROSS VEHICLE WEIGHT", "PREMIUM BAND", "THRESHOLD"
        }

        has_categorical_slabs = False
        slab_condition = None
        for s in slabs_in:
            cond = str(s.get("condition_field") or "").strip().upper()
            if cond:
                slab_condition = s.get("condition_field")
                if cond not in allowed_numeric_fields:
                    has_categorical_slabs = True
                    break
            orig_text = str(s.get("original_text") or "").upper()
            if any(k in orig_text for k in ["NCB", "CPA", "HP", "FLEET", "PARTNER"]):
                has_categorical_slabs = True
                break

        if is_slab and (not slabs_in or has_categorical_slabs):
            is_slab = False
            # Flatten/collapse first slab rates to main rule fields if main rule rates are null
            if slabs_in:
                first_slab = slabs_in[0]
                if payin_od is None: payin_od = first_slab.get("payin_od")
                if payin_tp is None: payin_tp = first_slab.get("payin_tp")
                if payin_net is None: payin_net = first_slab.get("payin_net")
                if payout_od is None: payout_od = first_slab.get("payout_od")
                if payout_tp is None: payout_tp = first_slab.get("payout_tp")
                if payout_net is None: payout_net = first_slab.get("payout_net")
                
                cond_val = first_slab.get("original_text") or first_slab.get("condition_field") or ""
                cond_val_upper = str(cond_val).upper()
                if "NCB" in cond_val_upper:
                    rule_data["ncb_status"] = cond_val
                elif "CPA" in cond_val_upper:
                    rule_data["cpa_status"] = cond_val
                else:
                    if rule_data["remarks"] == "ALL" or not rule_data["remarks"]:
                        rule_data["remarks"] = f"Condition: {cond_val}"
                    else:
                        rule_data["remarks"] = f"{rule_data['remarks']}; Condition: {cond_val}"
            slabs_in = []

        # Generate structured explanation with fallback to original row explanation
        explanation_val = row.get("explanation")
        if not explanation_val:
            if is_slab:
                explanation_val = (
                    f"Reason: Detected numeric slab ranges for '{slab_condition or 'Discount/Age/IDV/CC'}'. "
                    f"Generated Slabs: " + ", ".join([f"{s.get('slab_from') or 0}-{s.get('slab_to') if s.get('slab_to') not in (None, 'OPEN', 'MAX') else 'MAX'}" for s in slabs_in]) + ". "
                    f"Original Text: {source}"
                )
            else:
                explanation_val = (
                    f"Stored as NON_SLAB. Reason: Commission depends on categorical condition or remarks (no numeric boundaries). "
                    f"CRM slab fields only accept numeric values. Original Text: {source}"
                )
        else:
            # If we programmatically forced a slab to non-slab, adjust the explanation to explain the override
            if (row.get("commission_type") == "SLAB") and not is_slab:
                explanation_val = (
                    f"Stored as NON_SLAB. Reason: Commission depends on categorical condition or remarks (no numeric boundaries). "
                    f"CRM slab fields only accept numeric values. Original Text: {source}. (Overridden from SLAB)"
                )

        # Add explanation to warnings
        warnings.append(f"Source Rule: {explanation_val}")

        rule_data["validation_status"] = status
        rule_data["warnings"] = warnings
        rule_data["raw_json"] = row

        if is_slab:
            rule_data["commission_type"] = "SLAB"
            rule_data["slab_configuration"] = True
            
            for f in ("payin_od", "payout_od", "payin_tp", "payout_tp", "payin_net", "payout_net",
                      "payin_reward", "payout_reward", "payin_scheme", "payout_scheme"):
                rule_data[f] = None
                
            rule_data["slabs"] = self._tiers_to_slabs(slabs_in)
            
            dup_warnings = check_duplicate_slab_ranges(rule_data["slabs"])
            if dup_warnings:
                rule_data["warnings"] = list(rule_data["warnings"]) + dup_warnings
                rule_data["validation_status"] = "WARNING"
        else:
            rule_data["commission_type"] = "NON_SLAB"
            rule_data["slab_configuration"] = False
            rule_data["payin_od"] = payin_od
            rule_data["payout_od"] = payout_od
            rule_data["payin_tp"] = payin_tp
            rule_data["payout_tp"] = payout_tp
            rule_data["payin_net"] = payin_net
            rule_data["payout_net"] = payout_net
            rule_data["payin_reward"] = payin_reward
            rule_data["payout_reward"] = payout_reward
            rule_data["payin_scheme"] = payin_scheme
            rule_data["payout_scheme"] = payout_scheme
            rule_data["slabs"] = []

        return rule_data

    def _clean_numeric_boundary(self, val: Any) -> Optional[float]:
        if val is None:
            return None
        val_str = str(val).strip().upper()
        if val_str in ("OPEN", "NA", "N/A", "DEFAULT", "ABOVE", "BELOW", "ANY", ""):
            return None
        
        # Clean the string, keeping only digits, decimal point, and minus sign
        cleaned = ""
        for char in val_str:
            if char.isdigit() or char == '.' or char == '-':
                cleaned += char
                
        if not cleaned:
            return None
            
        try:
            multiplier = 1.0
            # Support Lakhs / Lakh / L
            if "LAKH" in val_str:
                multiplier = 100000.0
            # Support K (if representing thousand, e.g. "50k" -> 50000)
            elif "K" in val_str and not any(unit in val_str for unit in ("KG", "CC")):
                multiplier = 1000.0
                
            return float(cleaned) * multiplier
        except ValueError:
            return None

    def _tiers_to_slabs(self, tiers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Converts LLM-extracted discount-percentage tiers into SlabDetail dicts,
        supporting both the old discount_from_pct format and the new slab_from format.
        """
        normalized = []
        prev_to = None
        for t in tiers:
            frm = t.get("discount_from_pct")
            if frm is None:
                frm = t.get("slab_from")
            to = t.get("discount_to_pct")
            if to is None:
                to = t.get("slab_to")
                
            # If bounds touch, bump the lower limit of the next tier
            if prev_to is not None and frm is not None and frm == prev_to:
                try:
                    frm = float(frm) + 1
                except (ValueError, TypeError):
                    pass
            
            normalized.append({**t, "_resolved_from": frm, "_resolved_to": to})
            prev_to = to if to is not None else prev_to

        slabs = []
        for t in normalized:
            slab_from = self._clean_numeric_boundary(t.get("_resolved_from"))
            slab_to = self._clean_numeric_boundary(t.get("_resolved_to"))

            od_val = t.get("commission_od_pct")
            if od_val is None:
                od_val = t.get("payin_od")
                
            tp_val = t.get("commission_tp_pct")
            if tp_val is None:
                tp_val = t.get("payin_tp")
                
            net_val = t.get("commission_net_pct")
            if net_val is None:
                net_val = t.get("payin_net")

            rate_buckets = (
                ("OD", "payin_od", od_val),
                ("TP", "payin_tp", tp_val),
                ("NET", "payin_net", net_val),
            )
            for premium_type, payin_field, value in rate_buckets:
                if value is None:
                    continue
                
                # Check for explicit payout values or default to 80%
                payout_field = "payout_" + premium_type.lower()
                payout_val = t.get(payout_field)
                if payout_val is None:
                    try:
                        payout_val = round(float(value) * 0.8, 6) if value is not None else None
                    except (ValueError, TypeError):
                        payout_val = None

                slab = {
                    "payin_type": t.get("payin_type") or "PERCENTAGE",
                    "premium_type": premium_type,
                    "slab_from": slab_from,
                    "slab_to": slab_to,
                    "payin_od": None,
                    "payout_od": None,
                    "payin_tp": None,
                    "payout_tp": None,
                    "payin_net": None,
                    "payout_net": None,
                    "condition_field": t.get("condition_field"),
                    "operator": t.get("operator"),
                    "value": t.get("value"),
                    "original_text": t.get("original_text")
                }
                slab[payin_field] = value
                slab[payout_field] = payout_val
                slabs.append(slab)
        return slabs

    def _ocr_page_table(self, file_bytes: bytes, page_idx: int) -> Optional[List[List[str]]]:
        if fitz is None or pytesseract is None or Image is None:
            print("  [OCR SKIP] pytesseract/PyMuPDF not available in this environment.")
            return None
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            data = pytesseract.image_to_data(img, output_type=Output.DICT)
        except Exception as e:
            print(f"  [OCR ERROR] Page {page_idx + 1}: {e}")
            return None

        lines: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
        n = len(data.get("text", []))
        for i in range(n):
            word = data["text"][i].strip()
            if not word:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            lines.setdefault(key, []).append({
                "text": word,
                "left": data["left"][i],
                "width": data["width"][i],
                "top": data["top"][i],
            })

        if not lines:
            return None

        ordered_lines = sorted(lines.values(), key=lambda words: min(w["top"] for w in words))

        header_words = sorted(ordered_lines[0], key=lambda w: w["left"])
        columns: List[Dict[str, Any]] = []
        for w in header_words:
            if columns and w["left"] - columns[-1]["end"] < 40:
                columns[-1]["text"] += " " + w["text"]
                columns[-1]["end"] = w["left"] + w["width"]
            else:
                columns.append({"text": w["text"], "start": w["left"], "end": w["left"] + w["width"]})

        if len(columns) < 2:
            return None

        col_starts = [c["start"] for c in columns]

        def assign_column(x: int) -> int:
            return min(range(len(col_starts)), key=lambda idx: abs(x - col_starts[idx]))

        table_rows = [[c["text"] for c in columns]]
        for line_words in ordered_lines[1:]:
            row_cells = ["" for _ in columns]
            for w in sorted(line_words, key=lambda w: w["left"]):
                col_idx = assign_column(w["left"])
                row_cells[col_idx] = (row_cells[col_idx] + " " + w["text"]).strip()
            table_rows.append(row_cells)

        return table_rows
