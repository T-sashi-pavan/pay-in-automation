import base64
import io
import json
import os
import shutil
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

SLAB CLASSIFICATION RULES:
Determine the commission_type ('SLAB' or 'NON_SLAB') based on these rules:
A record is SLAB only if commission changes based on any of these parameters:
- Discount
- Vehicle Age
- IDV
- Sum Insured
- Premium Band
- CC (Engine capacity)
- GVW (Gross Vehicle Weight)
- Threshold
- Range
- From / To / Upto / Above / Below / Greater than / Less than / >= / <= / Between / Increment
Otherwise, classify as NON_SLAB.

FIELD EXTRACTION RULES:
- lob: Always "Motor". Ignore Health, Marine, Engineering etc.
- insurer: Extract name of the insurer company (e.g. "Oriental", "United India", "National", "New India", "ICICI", "Go Digit", "Tata AIG", "Shriram", etc.).
- product: If explicitly mentioned, store value; otherwise "ALL".
- sub_product: Extract wherever available. If missing, "NA".
- policy_type: Comprehensive, Standalone OD, Third Party, Package, Liability, etc. If absent, "ALL".
- plan_type: Extract plan duration (e.g. 1+1, 1+3, 3+3, 5+5, etc.). If absent, "ALL".
- file_type: Extract "New", "Renewal", "Rollover", etc. If absent, "ALL".
- class: Extract vehicle class name (e.g. Private Car, Two Wheeler, Commercial Vehicle, etc.). If absent, "ALL".
- sub_class: Extract subclass/segment details (e.g. GCV with GVW > 40000 Kg upto 50000 Kg). If absent, "ALL".
- make: Extract manufacturer (e.g. Maruti, Tata, Hyundai, Mahindra, RE, Bajaj, Hero, Honda). Map to standard uppercase name (e.g., "MARUTI"), otherwise "ALL".
- model: Extract vehicle model (e.g. Alto 800, Swift, Nexon, Activa, Splendor, Pulsar, Ace, Dost). If absent, "ALL".
- fuel_type: Petrol, Diesel, Electric, CNG, etc. If absent, "ALL".
- cpa: CPA status (YES, NO, or ALL). Set to YES if CPA is mentioned as included/with CPA; NO if excluded/without CPA.
- ncb: NCB status (YES, NO, or ALL). Set to YES if NCB cases or NCB >20% is shown; NO if without NCB/no NCB.
- vehicle_age: Vehicle age details (e.g. "Brand New", "0-5 years", "Age = 0", "Age >= 1"). If absent, "ALL".
- partner_type: Channel name like POSP, MISP, Broker, OEM Dealer, etc. If absent, "All Partners".
- state: Extract every state name or abbreviation (multiple allowed).
- zone: Extract North, South, East, West, Central, etc. If absent, "ALL".
- rto: Extract all RTO codes. If absent, "ALL".
- source: Store the original source paragraph or heading where this rule resides.
- remarks: Store any unmatched business restrictions, clauses, or footnotes. NEVER discard text.
- commission_type: "SLAB" or "NON_SLAB" based on slab classification rules.
- premium_type: Infer from commission text. Set to "OD" (if on OD premium), "TP" (if TP premium), or "NET" (if Net premium). Never assign all three unless explicitly stated.
- payin_od: Commission OD percentage as a number (e.g. 15.0 or null).
- payin_tp: Commission TP percentage as a number (e.g. 2.5 or null).
- payin_net: Commission Net percentage as a number (e.g. 20.0 or null).
- payout_od: Payout OD percentage as a number if explicitly stated, otherwise null.
- payout_tp: Payout TP percentage as a number if explicitly stated, otherwise null.
- payout_net: Payout Net percentage as a number if explicitly stated, otherwise null.
- payin_reward: Commission Reward percentage if explicitly stated, otherwise null.
- payout_reward: Payout Reward percentage if explicitly stated, otherwise null.
- payin_scheme: Commission Scheme percentage if explicitly stated, otherwise null.
- payout_scheme: Payout Scheme percentage if explicitly stated, otherwise null.
- explanation: Store the original source paragraph/text (e.g. "Discount upto 30% -> 20% on OD Premium -> 50% on TP Premium") to help users verify extraction.
- slabs: If commission_type is SLAB, return the array of slab tiers. Otherwise, return an empty array or null.
  Each slab tier object must contain:
  - payin_type: "PERCENTAGE" or "FLAT".
  - premium_type: "OD", "TP", or "NET" (inferred from commission text).
  - slab_from: Slab start limit (number or string, e.g. 0 or ">30"). Do NOT invent ranges. Keep the original business meaning.
  - slab_to: Slab end limit (number or string, e.g. 30 or "OPEN").
  - payin_od: OD rate for this slab tier (number or null).
  - payin_tp: TP rate for this slab tier (number or null).
  - payin_net: Net rate for this slab tier (number or null).
  - payout_od: Payout OD rate if explicitly stated (number or null).
  - payout_tp: Payout TP rate if explicitly stated (number or null).
  - payout_net: Payout Net rate if explicitly stated (number or null).
  - condition_field: The field name the slab is based on (e.g. "Discount", "Vehicle Age", "GVW", "CC", "IDV").
  - operator: Comparison operator (e.g. ">", "<=", "=", "between", or null).
  - value: The boundary value if single, or null.
  - original_text: The original text representing this slab tier (e.g. "Discount upto 30%").
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
            "provider": None, "pages_sent": 0, "input_tokens": 0, "output_tokens": 0,
            "total_tokens": 0, "pages_capped": 0, "errors": 0,
        }

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            print(f"\n[STARTING PDF PARSING] '{filename}' — {len(pdf.pages)} page(s) detected")

            for page_idx, page in enumerate(pdf.pages):
                page_num = page_idx + 1
                text = page.extract_text() or ""

                if usage["pages_sent"] >= PDF_VISION_MAX_PAGES:
                    usage["pages_capped"] += 1
                    print(f"  [COST GUARD] Page {page_num} skipped — reached PDF_VISION_MAX_PAGES={PDF_VISION_MAX_PAGES} for this upload.")
                    continue

                count = -1
                if text.strip():
                    count = self._llm_text_extract_page(
                        text, page_idx, filename, company, existing_keys, all_parsed_rules, usage
                    )
                    if count >= 0:
                        print(f"  [TABLE COMPLETED] Extracted {count} rules from Page {page_num} via text LLM.")
                        continue

                count = self._llm_vision_extract_page(
                    file_bytes, page_idx, filename, company, existing_keys, all_parsed_rules, usage
                )
                if count >= 0:
                    print(f"  [TABLE COMPLETED] Extracted {count} rules from Page {page_num} via vision LLM.")
                else:
                    ocr_table = self._ocr_page_table(file_bytes, page_idx)
                    if not ocr_table or len(ocr_table) < 2:
                        print(f"  [PAGE SKIP] Page {page_num} is scanned and OCR could not reconstruct a table.")
                        continue
                    headers, data_rows = ocr_table[0], ocr_table[1:]
                    sheet_name = f"Page {page_num} (OCR)"
                    count = self.excel_parser.parse_table(
                        headers, data_rows, sheet_name, filename, company, existing_keys, all_parsed_rules
                    )
                    print(f"  [TABLE COMPLETED] Extracted {count} rules from '{sheet_name}' via OCR.")

        final_rules = self.excel_parser._group_and_merge_rules(all_parsed_rules)
        before = len(final_rules)
        final_rules = [r for r in final_rules if not is_rule_effectively_empty(r)]
        dropped = before - len(final_rules)
        if dropped:
            print(f"  [DATA QUALITY] Dropped {dropped} rule(s) with no usable data.")

        if usage["pages_sent"] > 0:
            print(
                f"\n[LLM USAGE] provider={usage['provider']} | pages_sent={usage['pages_sent']} "
                f"| errors={usage['errors']} | pages_capped={usage['pages_capped']}\n"
                f"  input_tokens={usage['input_tokens']:,} | output_tokens={usage['output_tokens']:,} "
                f"| total_tokens={usage['total_tokens']:,}\n"
            )

        print(f"[PDF PARSING COMPLETED] Grouped {len(all_parsed_rules)} rules into {len(final_rules)} merged rules.")
        return final_rules

    def _render_page_png(self, file_bytes: bytes, page_idx: int) -> Optional[bytes]:
        if fitz is None:
            return None
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pix = doc[page_idx].get_pixmap(matrix=fitz.Matrix(2, 2))
            return pix.tobytes("png")
        except Exception as e:
            print(f"  [LLM VISION ERROR] Page {page_idx + 1} render failed: {e}")
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
            print(f"  [LLM VISION ERROR] Page {page_idx + 1} (Claude): {e}")
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
            print(f"  [LLM TEXT ERROR] Page {page_idx + 1} (Claude): {e}")
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
            response = client.chat.completions.create(
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
            self._record_usage(usage, "openai", page_idx + 1, response.usage.prompt_tokens, response.usage.completion_tokens)
            content = response.choices[0].message.content
            data = json.loads(content) if content else {}
            rows = data.get("rows", [])
        except Exception as e:
            usage["errors"] += 1
            print(f"  [LLM VISION ERROR] Page {page_idx + 1} (OpenAI): {e}")
            return -1
        return self._append_llm_rows(rows, company, filename, page_idx + 1, existing_keys, all_parsed_rules)

    def _openai_text_extract_page(
        self, text_content: str, page_idx: int, filename: Optional[str], company: str,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]], usage: Dict[str, Any]
    ) -> int:
        try:
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=OPENAI_VISION_MODEL,
                max_tokens=8192,
                response_format={"type": "json_schema", "json_schema": OPENAI_RESPONSE_SCHEMA},
                messages=[{
                    "role": "user",
                    "content": f"{LLM_EXTRACTION_PROMPT}\n\nHere is the raw text extracted from page {page_idx + 1}:\n{text_content}",
                }],
            )
            self._record_usage(usage, "openai", page_idx + 1, response.usage.prompt_tokens, response.usage.completion_tokens)
            content = response.choices[0].message.content
            data = json.loads(content) if content else {}
            rows = data.get("rows", [])
        except Exception as e:
            usage["errors"] += 1
            print(f"  [LLM TEXT ERROR] Page {page_idx + 1} (OpenAI): {e}")
            return -1
        return self._append_llm_rows(rows, company, filename, page_idx + 1, existing_keys, all_parsed_rules)

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
            print(f"  [LLM VISION ERROR] Page {page_idx + 1} (Gemini): {e}")
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
            print(f"  [LLM TEXT ERROR] Page {page_idx + 1} (Gemini): {e}")
            return -1
        return self._append_llm_rows(rows, company, filename, page_idx + 1, existing_keys, all_parsed_rules)

    def _record_usage(self, usage: Dict[str, Any], provider: str, page_num: int, input_tokens: int, output_tokens: int) -> None:
        usage["provider"] = provider
        usage["pages_sent"] += 1
        usage["input_tokens"] += input_tokens
        usage["output_tokens"] += output_tokens
        usage["total_tokens"] += input_tokens + output_tokens
        print(f"  [LLM USAGE] Page {page_num} ({provider}): input={input_tokens:,} output={output_tokens:,} tokens")

    def _append_llm_rows(
        self, rows: List[Dict[str, Any]], company: str, filename: Optional[str], page_num: int,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]]
    ) -> int:
        count = 0
        for row in rows:
            rule_dict = self._llm_row_to_rule(row, company, filename, page_num, existing_keys)
            if rule_dict:
                all_parsed_rules.append(rule_dict)
                count += 1
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
        remarks = row.get("remarks") or "ALL"

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
            "remarks": remarks,
        }

        # Validate
        status, warnings = RuleValidator.validate_rule(rule_data, existing_keys)
        
        # Add explanation panel text under Validation Warnings
        explanation = row.get("explanation")
        if explanation:
            warnings.append(f"Source Rule: {explanation}")

        rule_data["validation_status"] = status
        rule_data["warnings"] = warnings
        rule_data["raw_json"] = row

        # Handle slabs
        is_slab = (row.get("commission_type") == "SLAB")
        if is_slab:
            rule_data["commission_type"] = "SLAB"
            rule_data["slab_configuration"] = True
            
            # Reset direct rule rate fields
            for f in ("payin_od", "payout_od", "payin_tp", "payout_tp", "payin_net", "payout_net",
                      "payin_reward", "payout_reward", "payin_scheme", "payout_scheme"):
                rule_data[f] = None
                
            rule_data["slabs"] = self._tiers_to_slabs(row.get("slabs") or [])
            
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
            slab_from = t.get("_resolved_from")
            slab_to = t.get("_resolved_to")
            
            # Try to convert numeric bounds to float
            try:
                if slab_from is not None:
                    slab_from = float(str(slab_from).replace("%", "").strip())
            except ValueError:
                pass
            try:
                if slab_to is not None:
                    if str(slab_to).strip().upper() == "OPEN":
                        slab_to = None
                    else:
                        slab_to = float(str(slab_to).replace("%", "").strip())
            except ValueError:
                pass

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
