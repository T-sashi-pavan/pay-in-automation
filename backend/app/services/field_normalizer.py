import re
from typing import Any, Dict, Optional

# Shared, display-time normalization rules — applied in the API serializer,
# not baked into the database. Raw stored values (often null/blank straight
# out of the parser) are left untouched for editing/audit; every response
# the frontend renders instead shows a sensible default per field so nothing
# reads as an empty/NA dead end unless "NA" is itself the correct value.


def clean(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.upper() in ("NAN", "NONE", "N/A"):
        return None
    return s


def default_or(value: Any, default: str) -> str:
    v = clean(value)
    return v if v is not None else default


PLAN_TYPE_RE = re.compile(
    r'(\d+)\s*(?:yr|year)s?\s*OD\s*\+\s*(\d+)\s*(?:yr|year)s?\s*TP', re.IGNORECASE
)


def derive_plan_type(
    plan_type: Optional[str],
    policy_type: Optional[str],
    product: Optional[str],
    sub_class: Optional[str],
    remarks: Optional[str],
    raw_json: Optional[Dict[str, Any]],
) -> str:
    """
    "1 Yr OD + 1 Yr TP" style plan descriptions aren't always their own
    column — sometimes they're folded into a product/remarks cell (e.g.
    "Honda 1yr OD + 1yr TP"). Search the fields most likely to carry it,
    then the sheet's raw parsed values, before giving up with "ALL".
    """
    for val in (plan_type, policy_type, product, sub_class, remarks):
        if not val:
            continue
        m = PLAN_TYPE_RE.search(str(val))
        if m:
            return f"{m.group(1)} Yr OD + {m.group(2)} Yr TP"
    if raw_json:
        for v in raw_json.values():
            if not v:
                continue
            m = PLAN_TYPE_RE.search(str(v))
            if m:
                return f"{m.group(1)} Yr OD + {m.group(2)} Yr TP"
    return "ALL"


def compute_payout(payin: Optional[float]) -> Optional[float]:
    """Payout is always 80% of payin — a derived value, never independently stored."""
    if payin is None:
        return None
    return round(payin * 0.8, 6)
