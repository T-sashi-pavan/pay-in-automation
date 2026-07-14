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

# On Windows, the Tesseract-OCR installer doesn't always add itself to PATH,
# and pytesseract only looks on PATH by default. Auto-detect the common
# install locations so OCR works right after installing, with no manual
# PATH/env-var setup required.
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

# Default to the cheap/fast tier for every provider — vision-based table
# extraction is a well-structured task these smaller models handle well, and
# a shared/company API key shouldn't default to the most expensive option.
# Override via env var to force a bigger model for a specific deployment.
ANTHROPIC_VISION_MODEL = os.getenv("ANTHROPIC_VISION_MODEL", "claude-haiku-4-5-20251001")
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")

# Cost-safety net: a company API key can be drained by an unexpectedly huge
# scanned document. Caps how many pages per upload get sent to a paid vision
# API — remaining scanned pages beyond this are skipped (not silently billed).
PDF_VISION_MAX_PAGES = int(os.getenv("PDF_VISION_MAX_PAGES", "60"))

LLM_EXTRACTION_PROMPT = """You are reading one page of a scanned insurance commission-grid document. \
This application only tracks MOTOR DEPARTMENT (vehicle insurance) commission data — Two Wheeler, Private \
Car, GCV/Commercial Vehicle, PCCV/Passenger Carrying Vehicle, Miscellaneous vehicle classes, etc. If this \
page's table covers a DIFFERENT line of business (Marine, Fire, Engineering, Health, Life, Rewards/Incentives, \
Liability, or any non-vehicle product), return an empty rows list — do not extract those rows.

Extract every commission-rule row visible in the table on this page.

Typical columns: Sr No | Category of Vehicle | Type of Policy | Maximum Commission | Applicability of State \
| Applicability of Class of Vehicle (the exact columns can vary page to page — use your best judgement based \
on what is actually printed).

For each row, record the following fields:
- sr_no: the row's serial number label (e.g. "1.a", "3.f"), or null if not shown.
- category: the "Category of Vehicle" text.
- policy_type: the "Type of Policy" text.
- state: the state-applicability text, including any "except"/"excluding" clauses, or null if not shown.
- class_of_vehicle: the class-of-vehicle applicability text, or null.
- note: any other qualifying condition printed for this row (vehicle age, brand-new-only, etc.), or null.
- is_slab: true only if the "Maximum Commission" cell contains MULTIPLE discount-percentage-based tiers \
(e.g. "a) Discount upto 40%: 30% OD+90% TP; b) Discount 40-70%: 25% OD+85% TP; c) Discount >70%: 20% OD+80% TP").
  - If true, fill "tiers": a list of {discount_from_pct, discount_to_pct, commission_od_pct, commission_tp_pct, \
commission_net_pct}. Use null for discount_to_pct on the final open-ended tier (e.g. "exceeding 70%"). Each tier \
should fill EITHER commission_od_pct/commission_tp_pct (when OD and TP get different rates) OR \
commission_net_pct alone (when the tier states one flat rate "on Net Premium (OD+TP)") — never guess an OD/TP \
split for a rate that was only ever stated as a single Net figure.
  - If false, fill commission_od_pct / commission_tp_pct / commission_net_pct with whichever rate(s) actually \
apply (e.g. "50% on Net Premium (OD+TP)" means both OD and TP get 50% via commission_net_pct=50; \
"2.5% on TP premium" means only commission_tp_pct=2.5).

If this page has no commission table at all (a cover page, terms & conditions, section divider, etc.), return an \
empty rows list. Be exhaustive — transcribe every row on the page, not a sample. All percentages must be plain \
numbers, not strings."""

EXTRACTION_TOOL_SCHEMA = {
    "name": "extract_commission_rows",
    "description": "Record every commission-rule row read from this page's table.",
    "input_schema": {
        "type": "object",
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "sr_no": {"type": ["string", "null"]},
                        "category": {"type": ["string", "null"]},
                        "policy_type": {"type": ["string", "null"]},
                        "state": {"type": ["string", "null"]},
                        "class_of_vehicle": {"type": ["string", "null"]},
                        "note": {"type": ["string", "null"]},
                        "is_slab": {"type": "boolean"},
                        "commission_od_pct": {"type": ["number", "null"]},
                        "commission_tp_pct": {"type": ["number", "null"]},
                        "commission_net_pct": {"type": ["number", "null"]},
                        "tiers": {
                            "type": ["array", "null"],
                            "items": {
                                "type": "object",
                                "properties": {
                                    "discount_from_pct": {"type": ["number", "null"]},
                                    "discount_to_pct": {"type": ["number", "null"]},
                                    "commission_od_pct": {"type": ["number", "null"]},
                                    "commission_tp_pct": {"type": ["number", "null"]},
                                    "commission_net_pct": {"type": ["number", "null"]},
                                },
                                "required": ["discount_from_pct", "discount_to_pct"],
                            },
                        },
                    },
                    "required": ["is_slab"],
                },
            }
        },
        "required": ["rows"],
    },
}

if genai_types is not None:
    _GEMINI_TIER_SCHEMA = genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "discount_from_pct": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "discount_to_pct": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "commission_od_pct": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "commission_tp_pct": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "commission_net_pct": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
        },
    )
    _GEMINI_ROW_SCHEMA = genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "sr_no": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "category": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "policy_type": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "state": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "class_of_vehicle": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "note": genai_types.Schema(type=genai_types.Type.STRING, nullable=True),
            "is_slab": genai_types.Schema(type=genai_types.Type.BOOLEAN),
            "commission_od_pct": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "commission_tp_pct": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "commission_net_pct": genai_types.Schema(type=genai_types.Type.NUMBER, nullable=True),
            "tiers": genai_types.Schema(type=genai_types.Type.ARRAY, items=_GEMINI_TIER_SCHEMA, nullable=True),
        },
        required=["is_slab"],
    )
    GEMINI_RESPONSE_SCHEMA = genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={"rows": genai_types.Schema(type=genai_types.Type.ARRAY, items=_GEMINI_ROW_SCHEMA)},
        required=["rows"],
    )
else:
    GEMINI_RESPONSE_SCHEMA = None

# OpenAI Structured Outputs (strict mode) requires every object to set
# additionalProperties: false and list every property (including nullable
# ones) in "required" — nullability is expressed via a ["type", "null"] union.
_OPENAI_TIER_SCHEMA = {
    "type": "object",
    "properties": {
        "discount_from_pct": {"type": ["number", "null"]},
        "discount_to_pct": {"type": ["number", "null"]},
        "commission_od_pct": {"type": ["number", "null"]},
        "commission_tp_pct": {"type": ["number", "null"]},
        "commission_net_pct": {"type": ["number", "null"]},
    },
    "required": ["discount_from_pct", "discount_to_pct", "commission_od_pct", "commission_tp_pct", "commission_net_pct"],
    "additionalProperties": False,
}
_OPENAI_ROW_SCHEMA = {
    "type": "object",
    "properties": {
        "sr_no": {"type": ["string", "null"]},
        "category": {"type": ["string", "null"]},
        "policy_type": {"type": ["string", "null"]},
        "state": {"type": ["string", "null"]},
        "class_of_vehicle": {"type": ["string", "null"]},
        "note": {"type": ["string", "null"]},
        "is_slab": {"type": "boolean"},
        "commission_od_pct": {"type": ["number", "null"]},
        "commission_tp_pct": {"type": ["number", "null"]},
        "commission_net_pct": {"type": ["number", "null"]},
        "tiers": {"type": ["array", "null"], "items": _OPENAI_TIER_SCHEMA},
    },
    "required": [
        "sr_no", "category", "policy_type", "state", "class_of_vehicle", "note", "is_slab",
        "commission_od_pct", "commission_tp_pct", "commission_net_pct", "tiers",
    ],
    "additionalProperties": False,
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
    Parses commission-grid tables out of a PDF.

    - Text-based PDFs are read directly via pdfplumber's native table extraction.
    - Scanned/rasterized PDFs (no extractable text) are read by a vision-capable
      LLM that looks at the rendered page image the same way a person would —
      this is what actually works for irregular, multi-shape scanned tables,
      unlike traditional OCR. Tried in order: Anthropic (ANTHROPIC_API_KEY),
      OpenAI (OPENAI_API_KEY), Gemini (GEMINI_API_KEY / GOOGLE_API_KEY) —
      whichever is configured first is used for the whole document.
    - If no key is configured, scanned pages fall back to a best-effort
      PyMuPDF-render + pytesseract-OCR + column-position heuristic, which is
      far less reliable (no semantic understanding of table structure) but
      requires no API key/cost.
    - Every vision API call's token usage is logged per page and totalled at
      the end (cost control for a shared/company API key), and no more than
      PDF_VISION_MAX_PAGES pages per upload are ever sent to a paid API.

    Every path emits the same flat "one row = one rule" shape (either routed
    through ExcelParserService.parse_table for the pdfplumber/OCR paths, or
    built directly for the LLM-vision path since the model already returns
    semantically-structured rows), so all three feed the same
    normalization/merge pipeline downstream.
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

                if text.strip():
                    tables = page.extract_tables() or []
                    if not tables:
                        continue
                    for t_idx, table in enumerate(tables):
                        rows = [[(c or "").strip() for c in row] for row in table if any(row)]
                        if len(rows) < 2:
                            continue
                        headers, data_rows = rows[0], rows[1:]
                        sheet_name = f"Page {page_num} Table {t_idx + 1}"
                        count = self.excel_parser.parse_table(
                            headers, data_rows, sheet_name, filename, company, existing_keys, all_parsed_rules
                        )
                        print(f"  [TABLE COMPLETED] Extracted {count} rules from '{sheet_name}'.")
                else:
                    # Scanned page — no extractable text at all. Prefer LLM vision
                    # (reliable); fall back to the Tesseract heuristic only if no
                    # API key is configured, the page cap is hit, or the call errors.
                    if usage["pages_sent"] >= PDF_VISION_MAX_PAGES:
                        usage["pages_capped"] += 1
                        print(f"  [COST GUARD] Page {page_num} skipped — reached PDF_VISION_MAX_PAGES={PDF_VISION_MAX_PAGES} for this upload.")
                    else:
                        llm_count = self._llm_vision_extract_page(
                            file_bytes, page_idx, filename, company, existing_keys, all_parsed_rules, usage
                        )
                        if llm_count >= 0:
                            print(f"  [TABLE COMPLETED] Extracted {llm_count} rules from Page {page_num} via {usage['provider']} vision.")
                            continue

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
            print(f"  [DATA QUALITY] Dropped {dropped} rule(s) with no usable data (likely OCR column-misread).")

        if usage["pages_sent"] > 0:
            print(
                f"\n[LLM VISION USAGE] provider={usage['provider']} | pages_sent={usage['pages_sent']} "
                f"| errors={usage['errors']} | pages_capped_by_PDF_VISION_MAX_PAGES={usage['pages_capped']}\n"
                f"  input_tokens={usage['input_tokens']:,} | output_tokens={usage['output_tokens']:,} "
                f"| total_tokens={usage['total_tokens']:,}\n"
                f"  NOTE: this is per-call token usage from the API response, not your account's remaining "
                f"balance/quota — no chat-completion API exposes remaining credit; check that on the "
                f"provider's billing dashboard (console.anthropic.com / platform.openai.com / aistudio.google.com)."
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

    def _llm_vision_extract_page(
        self, file_bytes: bytes, page_idx: int, filename: Optional[str], company: str,
        existing_keys: set, all_parsed_rules: List[Dict[str, Any]], usage: Dict[str, Any]
    ) -> int:
        """
        Renders the page to an image and asks a vision-capable LLM to read it
        directly, the same way a person visually reads a scanned table — this is
        what actually handles irregular/multi-shape scanned layouts that defeat a
        pure OCR + column-position heuristic. Tries Anthropic, then OpenAI, then
        Gemini, using whichever API key is actually configured (first match wins
        for the whole document, so usage isn't split across providers). Returns
        -1 (not a real count) if no provider is available or the call errored,
        signalling the caller to fall back to the Tesseract heuristic instead.
        `usage` is mutated in place with running token counts for this upload.
        """
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
                print(f"  [LLM VISION] Page {page_idx + 1}: Claude returned no structured result.")
                return 0
            rows = tool_use.input.get("rows", [])
        except Exception as e:
            usage["errors"] += 1
            print(f"  [LLM VISION ERROR] Page {page_idx + 1} (Claude): {e}")
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
        sr_no = row.get("sr_no")
        category = row.get("category")
        policy_type = row.get("policy_type")
        state_raw = row.get("state")
        class_of_vehicle = row.get("class_of_vehicle")
        note = row.get("note")

        remarks = " | ".join(filter(None, [
            f"Sr {sr_no}" if sr_no else None,
            note,
            f"(LLM vision extraction — {filename or 'PDF'} p.{page_num})",
        ]))

        rule_data: Dict[str, Any] = {
            "sheet_name": f"Page {page_num} (LLM Vision)",
            "lob": "Motor",
            "file_type": None,
            "insurance_company": company,
            "product": class_of_vehicle,
            "policy_type": policy_type,
            "plan_type": None,
            "sub_product": None,
            "class_": None,
            "sub_class": category,
            "make": None,
            "model": None,
            "fuel_type": None,
            "body_type": None,
            "vehicle_age_from": None,
            "vehicle_age_to": None,
            "cpa_status": None,
            "ncb_status": None,
            "partner_type": None,
            "state": self.normalizer.normalize_states(state_raw) if state_raw else None,
            "zone": None,
            "source": None,
            "rto": None,
            "effective_date": date.today(),
            "remarks": remarks or None,
        }

        status, warnings = RuleValidator.validate_rule(rule_data, existing_keys)
        rule_data["validation_status"] = status
        rule_data["warnings"] = warnings
        rule_data["raw_json"] = {
            "sr_no": sr_no, "category": category, "policy_type": policy_type,
            "state": state_raw, "class_of_vehicle": class_of_vehicle, "note": note,
        }

        if row.get("is_slab") and row.get("tiers"):
            rule_data["commission_type"] = "SLAB"
            rule_data["slab_configuration"] = True
            for f in ("payin_od", "payout_od", "payin_tp", "payout_tp", "payin_net", "payout_net",
                      "payin_reward", "payout_reward", "payin_scheme", "payout_scheme"):
                rule_data[f] = None
            rule_data["slabs"] = self._tiers_to_slabs(row["tiers"])
            dup_warnings = check_duplicate_slab_ranges(rule_data["slabs"])
            if dup_warnings:
                rule_data["warnings"] = list(rule_data["warnings"]) + dup_warnings
                rule_data["validation_status"] = "WARNING"
        else:
            rule_data["commission_type"] = "NON_SLAB"
            rule_data["slab_configuration"] = False
            rule_data["payin_od"] = row.get("commission_od_pct")
            rule_data["payout_od"] = None
            rule_data["payin_tp"] = row.get("commission_tp_pct")
            rule_data["payout_tp"] = None
            rule_data["payin_net"] = row.get("commission_net_pct")
            rule_data["payout_net"] = None
            rule_data["payin_reward"] = None
            rule_data["payout_reward"] = None
            rule_data["payin_scheme"] = None
            rule_data["payout_scheme"] = None
            rule_data["slabs"] = []

        return rule_data

    def _tiers_to_slabs(self, tiers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Converts LLM-extracted discount-percentage tiers into SlabDetail dicts,
        matching the established one-rate-bucket-per-row convention used by every
        real Excel-sourced slab (premium_type is always exactly one of OD/TP/NET,
        never a combined or made-up label like "DISCOUNT %"). A tier stating both
        an OD and a TP rate (e.g. "30% OD + 90% TP") becomes TWO slab rows sharing
        the same slab_from/slab_to boundary, one per rate bucket.

        Boundaries are also normalized to be non-overlapping: adjacent tiers whose
        upper/lower bounds touch (e.g. (0,40),(40,70)) get the next tier's lower
        bound bumped to upper+1, since discount bands in the source documents are
        always whole-number percentages — this reads as a real duplicate/overlap
        to anyone scanning the table otherwise, even though it's technically just
        an exclusive-vs-inclusive boundary convention.
        """
        normalized = []
        prev_to = None
        for t in tiers:
            frm = t.get("discount_from_pct")
            to = t.get("discount_to_pct")
            if prev_to is not None and frm is not None and frm == prev_to:
                frm = frm + 1
            normalized.append({**t, "discount_from_pct": frm, "discount_to_pct": to})
            prev_to = to if to is not None else prev_to

        slabs = []
        for t in normalized:
            slab_from = t.get("discount_from_pct")
            slab_to = t.get("discount_to_pct")
            rate_buckets = (
                ("OD", "payin_od", t.get("commission_od_pct")),
                ("TP", "payin_tp", t.get("commission_tp_pct")),
                ("NET", "payin_net", t.get("commission_net_pct")),
            )
            for premium_type, payin_field, value in rate_buckets:
                if value is None:
                    continue
                slab = {
                    "payin_type": "PERCENTAGE",
                    "premium_type": premium_type,
                    "slab_from": slab_from,
                    "slab_to": slab_to,
                    "payin_od": None,
                    "payout_od": None,
                    "payin_tp": None,
                    "payout_tp": None,
                    "payin_net": None,
                    "payout_net": None,
                }
                slab[payin_field] = value
                slabs.append(slab)
        return slabs

    def _ocr_page_table(self, file_bytes: bytes, page_idx: int) -> Optional[List[List[str]]]:
        """
        Best-effort table reconstruction from a scanned page: renders the page to an
        image via PyMuPDF, OCRs it with pytesseract, groups recognized words into
        lines (tesseract's own block/paragraph/line grouping), then assigns each
        word to a column by nearest x-position to the header line's word starts.
        Requires the system Tesseract-OCR binary to be installed — not just the
        pytesseract pip package (see requirements.txt note / deployment follow-up).
        This is only used as a fallback when no ANTHROPIC_API_KEY is configured.
        """
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

        # Use the first line as the header row to establish column boundaries —
        # words within 40px of each other merge into a single (multi-word) column header.
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
