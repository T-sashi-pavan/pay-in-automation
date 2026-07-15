"""
excel_export.py — Fast two-sheet .xlsx export using XlsxWriter.

XlsxWriter is used instead of openpyxl because it is a sequential, streaming
write-only library. Formats are defined once and reused; no per-cell style
objects are allocated; data is flushed incrementally. This reduces export time
from 2–10 minutes (openpyxl with cell-level styling) to under 30 seconds even
for 5 000+ rules.

Layout
──────
Sheet 1 "Non-Slab"
    One flat row per NON_SLAB rule, containing all business columns + rate
    columns.

Sheet 2 "Slab"
    CRM-Ready vertical-merged layout.  One header row, then one data row per
    slab tier.  Business-column cells for a given rule are merged vertically
    across all its tier rows.
"""

from io import BytesIO
from typing import Any, Dict, List, Optional

import xlsxwriter
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.models.commission_rule import CommissionRule
from backend.app.services.rule_serializer import serialize_commission_rule
from backend.app.services import master_data_service
from backend.app.services.field_normalizer import (
    clean, default_or, derive_plan_type, compute_payout
)

# ── Column definitions ───────────────────────────────────────────────────────

BUSINESS_COLUMNS: List[tuple] = [
    ("LOB", "lob"),
    ("File Type", "file_type"),
    ("Insurance Company", "insurance_company"),
    ("Product", "product"),
    ("Policy Type", "policy_type"),
    ("Plan Type", "plan_type"),
    ("Sub Product", "sub_product"),
    ("Class", "class"),
    ("Sub Class", "sub_class"),
    ("Make", "make"),
    ("Model", "model"),
    ("Fuel Type", "fuel_type"),
    ("Body Type", "body_type"),
    ("Vehicle Age From", "vehicle_age_from"),
    ("Vehicle Age To", "vehicle_age_to"),
    ("CPA Status", "cpa_status"),
    ("NCB Status", "ncb_status"),
    ("Partner Type", "partner_type"),
    ("State", "state"),
    ("Zone", "zone"),
    ("Source", "source"),
    ("RTO", "rto"),
    ("Effective Date", "effective_date"),
    ("Remarks", "remarks"),
]

NON_SLAB_RATE_COLUMNS: List[tuple] = [
    ("Pay-In OD", "payin_od"), ("Pay-Out OD", "payout_od"),
    ("Pay-In TP", "payin_tp"), ("Pay-Out TP", "payout_tp"),
    ("Pay-In Net", "payin_net"), ("Pay-Out Net", "payout_net"),
    ("Pay-In Reward", "payin_reward"), ("Pay-Out Reward", "payout_reward"),
    ("Pay-In Scheme", "payin_scheme"), ("Pay-Out Scheme", "payout_scheme"),
]

# Slab tier detail columns — written once per slab row (CRM-Ready layout)
SLAB_TIER_COLUMNS: List[tuple] = [
    ("Pay-In Type", "payin_type"),
    ("Premium Type", "premium_type"),
    ("Payin Slab From", "slab_from"),
    ("Payin Slab To", "slab_to"),
    ("Pay-In OD", "payin_od"),
    ("Pay-In TP", "payin_tp"),
    ("Pay-In Net", "payin_net"),
    ("Pay-Out OD", "payout_od"),
    ("Pay-Out TP", "payout_tp"),
    ("Pay-Out Net", "payout_net"),
]


def _col_width(max_char_len: int) -> float:
    """Clamp column width between 10 and 60 characters."""
    return min(max(max_char_len + 2, 10), 60)


def build_export_workbook(rules: List[CommissionRule], db: Session) -> BytesIO:
    """
    Generate a two-sheet .xlsx (Non-Slab, Slab) and return a seeked BytesIO.

    Uses xlsxwriter for fast sequential write performance.
    """
    non_slab_rules = [r for r in rules if r.commission_type != "SLAB"]
    slab_rules = [r for r in rules if r.commission_type == "SLAB"]

    buffer = BytesIO()
    wb = xlsxwriter.Workbook(buffer, {
        "in_memory": True,
        "strings_to_numbers": False,
        "strings_to_urls": False,
    })

    # ── Shared formats ────────────────────────────────────────────────────────

    FMT_HEADER = wb.add_format({
        "bold": True, "font_color": "#FFFFFF",
        "bg_color": "#4F46E5",
        "align": "center", "valign": "vcenter",
        "text_wrap": True,
        "border": 1, "border_color": "#4F46E5",
    })
    FMT_NORMAL = wb.add_format({
        "valign": "top", "text_wrap": True,
        "border": 1, "border_color": "#CCCCCC",
    })
    FMT_DEFAULTED = wb.add_format({
        "font_color": "#6D28D9",   # purple-700
        "valign": "top", "text_wrap": True,
        "border": 1, "border_color": "#CCCCCC",
    })
    FMT_SLAB_NORMAL = wb.add_format({
        "align": "center", "valign": "vcenter", "text_wrap": True,
        "border": 1, "border_color": "#CCCCCC",
    })
    FMT_SLAB_DEFAULTED = wb.add_format({
        "font_color": "#6D28D9",
        "align": "center", "valign": "vcenter", "text_wrap": True,
        "border": 1, "border_color": "#CCCCCC",
    })
    # Format for business-column cells in the slab sheet (top-aligned, normal)
    FMT_BIZ_NORMAL = wb.add_format({
        "valign": "top", "text_wrap": True,
        "border": 1, "border_color": "#CCCCCC",
    })
    FMT_BIZ_DEFAULTED = wb.add_format({
        "font_color": "#6D28D9",
        "valign": "top", "text_wrap": True,
        "border": 1, "border_color": "#CCCCCC",
    })
    # Separator border at the bottom of the last tier row of each rule
    FMT_SLAB_SEP = wb.add_format({
        "align": "center", "valign": "vcenter", "text_wrap": True,
        "top": 1, "top_color": "#CCCCCC",
        "left": 1, "left_color": "#CCCCCC",
        "right": 1, "right_color": "#CCCCCC",
        "bottom": 2, "bottom_color": "#4F46E5",
    })
    FMT_BIZ_SEP = wb.add_format({
        "valign": "top", "text_wrap": True,
        "top": 1, "top_color": "#CCCCCC",
        "left": 1, "left_color": "#CCCCCC",
        "right": 1, "right_color": "#CCCCCC",
        "bottom": 2, "bottom_color": "#4F46E5",
    })

    # ── NON-SLAB SHEET ────────────────────────────────────────────────────────

    ns_headers = [label for label, _ in BUSINESS_COLUMNS] + [label for label, _ in NON_SLAB_RATE_COLUMNS]
    n_biz = len(BUSINESS_COLUMNS)
    n_ns_cols = len(ns_headers)

    ws_ns = wb.add_worksheet("Non-Slab")
    ws_ns.freeze_panes(1, 0)

    # Header row (row 0 in xlsxwriter 0-indexed)
    for col_idx, label in enumerate(ns_headers):
        ws_ns.write(0, col_idx, label, FMT_HEADER)

    # Track column widths (start from header lengths)
    ns_widths = [len(h) for h in ns_headers]

    # Data rows (starting at row 1)
    for row_idx, rule in enumerate(non_slab_rules, start=1):
        data = serialize_commission_rule(rule, db, exclude_raw_json=True)
        defaulted = set(data.get("_defaulted_fields") or [])

        biz_values = [data.get(field) for _, field in BUSINESS_COLUMNS]
        rate_values = [data.get(field) for _, field in NON_SLAB_RATE_COLUMNS]
        row_values = biz_values + rate_values

        for col_idx, val in enumerate(row_values):
            # Choose format: defaulted fields get purple font
            if col_idx < n_biz:
                _, field = BUSINESS_COLUMNS[col_idx]
                fmt = FMT_DEFAULTED if field in defaulted else FMT_NORMAL
            else:
                fmt = FMT_NORMAL

            str_val = str(val) if val is not None else ""
            if len(str_val) > ns_widths[col_idx]:
                ns_widths[col_idx] = len(str_val)

            ws_ns.write(row_idx, col_idx, val if val is not None else "", fmt)

    # Set column widths
    for col_idx, w in enumerate(ns_widths):
        ws_ns.set_column(col_idx, col_idx, _col_width(w))

    # ── SLAB SHEET ────────────────────────────────────────────────────────────

    sl_headers = [label for label, _ in BUSINESS_COLUMNS] + [label for label, _ in SLAB_TIER_COLUMNS]
    n_tier = len(SLAB_TIER_COLUMNS)
    total_sl_cols = n_biz + n_tier

    ws_sl = wb.add_worksheet("Slab")
    ws_sl.freeze_panes(1, 0)

    # Header row
    for col_idx, label in enumerate(sl_headers):
        ws_sl.write(0, col_idx, label, FMT_HEADER)

    sl_widths = [len(h) for h in sl_headers]

    # Data rows — 0-indexed row cursor (header is row 0)
    current_row = 1  # next row to write

    for rule in slab_rules:
        data = serialize_commission_rule(rule, db, exclude_raw_json=True)
        defaulted = set(data.get("_defaulted_fields") or [])
        slabs = data.get("slabs") or [{}]

        biz_values = [data.get(field) for _, field in BUSINESS_COLUMNS]
        first_tier_row = current_row
        n_tiers = len(slabs)

        for tier_idx, slab in enumerate(slabs):
            slab_values = [slab.get(field) for _, field in SLAB_TIER_COLUMNS]
            slab_defaulted = set(slab.get("_defaulted_fields") or [])

            # Determine separator format (only last tier row of each rule)
            is_last_tier = (tier_idx == n_tiers - 1)

            # Write business columns (only on first tier row; subsequent rows are merged)
            if tier_idx == 0:
                for col_idx, (_, field) in enumerate(BUSINESS_COLUMNS):
                    val = biz_values[col_idx]
                    str_val = str(val) if val is not None else ""
                    if len(str_val) > sl_widths[col_idx]:
                        sl_widths[col_idx] = len(str_val)
                    fmt = FMT_BIZ_SEP if is_last_tier else (FMT_BIZ_DEFAULTED if field in defaulted else FMT_BIZ_NORMAL)
                    ws_sl.write(current_row, col_idx, val if val is not None else "", fmt)
            else:
                # Subsequent tier rows: business columns will be merged — write empty
                if is_last_tier:
                    for col_idx in range(n_biz):
                        ws_sl.write(current_row, col_idx, "", FMT_BIZ_SEP)

            # Write slab tier columns
            for col_idx, (_, field) in enumerate(SLAB_TIER_COLUMNS):
                abs_col = n_biz + col_idx
                val = slab_values[col_idx]
                str_val = str(val) if val is not None else ""
                if len(str_val) > sl_widths[abs_col]:
                    sl_widths[abs_col] = len(str_val)

                if is_last_tier:
                    fmt = FMT_SLAB_SEP
                elif field in slab_defaulted:
                    fmt = FMT_SLAB_DEFAULTED
                else:
                    fmt = FMT_SLAB_NORMAL

                ws_sl.write(current_row, abs_col, val if val is not None else "", fmt)

            current_row += 1

        last_tier_row = current_row - 1  # last row written for this rule

        # Merge business columns vertically across all tier rows of this rule
        if n_tiers > 1:
            for col_idx, (_, field) in enumerate(BUSINESS_COLUMNS):
                val = biz_values[col_idx]
                fmt = FMT_BIZ_DEFAULTED if field in defaulted else FMT_BIZ_NORMAL
                ws_sl.merge_range(
                    first_tier_row, col_idx,
                    last_tier_row, col_idx,
                    val if val is not None else "",
                    fmt,
                )

    # Set column widths
    for col_idx, w in enumerate(sl_widths):
        ws_sl.set_column(col_idx, col_idx, _col_width(w))

    wb.close()
    buffer.seek(0)
    return buffer


# ── Fast raw-SQL export path ─────────────────────────────────────────────────

def _to_pct(val: Any) -> Any:
    """Convert fractional percentages (0-1 range) to display values."""
    if val is None:
        return None
    try:
        f = float(val)
        if 0.0 < abs(f) <= 1.0:
            return round(f * 100.0, 4)
        return f
    except (ValueError, TypeError):
        return val


def _serialize_rule_dict(r: Dict[str, Any], slabs: List[Dict[str, Any]], db: Session) -> Dict[str, Any]:
    """
    Inline dict-based serialization equivalent to serialize_commission_rule().
    Accepts raw psycopg2/SQLAlchemy-core row dicts — no ORM objects needed.
    """
    payin_od   = _to_pct(r.get("payin_od"))
    payin_tp   = _to_pct(r.get("payin_tp"))
    payin_net  = _to_pct(r.get("payin_net"))
    payin_rew  = _to_pct(r.get("payin_reward"))
    payin_sch  = _to_pct(r.get("payin_scheme"))

    defaulted_fields: List[str] = []
    for field_key in (
        "lob", "file_type", "product", "policy_type", "plan_type", "sub_product",
        "class", "sub_class", "make", "model", "fuel_type", "body_type",
        "cpa_status", "ncb_status", "partner_type", "state", "zone", "source",
        "rto", "remarks",
    ):
        if clean(r.get(field_key)) is None:
            defaulted_fields.append(field_key)
    if r.get("vehicle_age_from") is None:
        defaulted_fields.append("vehicle_age_from")
    if r.get("vehicle_age_to") is None:
        defaulted_fields.append("vehicle_age_to")

    # Slab rows
    serialized_slabs: List[Dict[str, Any]] = []
    for s in slabs:
        s_od  = _to_pct(s.get("payin_od"))
        s_tp  = _to_pct(s.get("payin_tp"))
        s_net = _to_pct(s.get("payin_net"))
        s_defaults: List[str] = []
        if clean(s.get("payin_type")) is None:
            s_defaults.append("payin_type")
        if clean(s.get("premium_type")) is None:
            s_defaults.append("premium_type")
        if s.get("slab_from") is None:
            s_defaults.append("slab_from")
        if s.get("slab_to") is None:
            s_defaults.append("slab_to")
        serialized_slabs.append({
            "payin_type": default_or(s.get("payin_type"), "NET"),
            "premium_type": default_or(
                s.get("premium_type"),
                "OD" if s_od is not None else ("TP" if s_tp is not None else "NET"),
            ),
            "slab_from": s.get("slab_from") if s.get("slab_from") is not None else 1,
            "slab_to":   s.get("slab_to")   if s.get("slab_to")   is not None else "MAX",
            "payin_od":   s_od,
            "payout_od":  compute_payout(s_od),
            "payin_tp":   s_tp,
            "payout_tp":  compute_payout(s_tp),
            "payin_net":  s_net,
            "payout_net": compute_payout(s_net),
            "_defaulted_fields": s_defaults,
        })

    return {
        "lob":              default_or(r.get("lob"), "Motor"),
        "file_type":        default_or(r.get("file_type"), "ALL"),
        "insurance_company": r.get("insurance_company"),
        "product":          default_or(r.get("product"), "ALL"),
        "policy_type":      default_or(r.get("policy_type"), "ALL"),
        "plan_type":        default_or(
            r.get("plan_type"),
            derive_plan_type(
                r.get("plan_type"), r.get("policy_type"), r.get("product"),
                r.get("sub_class"), r.get("remarks"), None,   # skip raw_json
            ),
        ),
        "sub_product":      default_or(r.get("sub_product"), "ALL"),
        "class":            default_or(r.get("class"), "ALL"),
        "sub_class":        default_or(r.get("sub_class"), "ALL"),
        "make":             default_or(r.get("make"), "ALL"),
        "model":            default_or(r.get("model"), "ALL"),
        "fuel_type":        default_or(r.get("fuel_type"), "ALL"),
        "body_type":        default_or(r.get("body_type"), "ALL"),
        "vehicle_age_from": r.get("vehicle_age_from") if r.get("vehicle_age_from") is not None else 1,
        "vehicle_age_to":   r.get("vehicle_age_to")   if r.get("vehicle_age_to")   is not None else 50,
        "cpa_status":       default_or(r.get("cpa_status"), "ALL"),
        "ncb_status":       default_or(r.get("ncb_status"), "ALL"),
        "partner_type":     default_or(r.get("partner_type"), "All Partners"),
        "state":            default_or(r.get("state"), "ALL"),
        "zone":             default_or(r.get("zone"), "ALL"),
        "source":           default_or(r.get("source"), "ALL"),
        "rto":              default_or(r.get("rto"), "ALL"),
        "effective_date":   str(r.get("effective_date")) if r.get("effective_date") else None,
        "remarks":          default_or(r.get("remarks"), "ALL"),
        "commission_type":  r.get("commission_type"),
        "payin_od":         payin_od,
        "payout_od":        compute_payout(payin_od),
        "payin_tp":         payin_tp,
        "payout_tp":        compute_payout(payin_tp),
        "payin_net":        payin_net,
        "payout_net":       compute_payout(payin_net),
        "payin_reward":     payin_rew,
        "payout_reward":    compute_payout(payin_rew),
        "payin_scheme":     payin_sch,
        "payout_scheme":    compute_payout(payin_sch),
        "slabs":            serialized_slabs,
        "_defaulted_fields": defaulted_fields,
    }


def build_export_from_upload_id(
    upload_id: int,
    db: Session,
    commission_type_filter: Optional[str] = None,
) -> BytesIO:
    """
    Fast export path: fetches all rules for upload_id via two raw SQL
    queries (no ORM hydration overhead), then builds the xlsxwriter workbook
    from plain dicts.

    Compared to the ORM path (build_export_workbook), this reduces the DB
    fetch from 30-64 s to under 5 s for 5 000+ rules.

    Args:
        upload_id: The primary key of the UploadHistory record.
        db:        An active SQLAlchemy Session (used for master-data cache
                   lookups and to borrow the underlying connection).
        commission_type_filter:  If provided, only export "SLAB" or "NON_SLAB".
    """
    # ── 1. Fetch rules via raw SQL (no raw_json) ──────────────────────────────
    rule_sql = text("""
        SELECT id, upload_id, lob, file_type, insurance_company, product, policy_type,
               plan_type, sub_product, "class", sub_class, make, model, fuel_type, body_type,
               vehicle_age_from, vehicle_age_to, cpa_status, ncb_status, partner_type,
               state, zone, source, rto, effective_date, remarks,
               commission_type, slab_configuration,
               payin_od, payin_tp, payin_net, payin_reward, payin_scheme,
               validation_status
        FROM commission_rules
        WHERE upload_id = :upload_id
        ORDER BY id ASC
    """)
    cursor = db.execute(rule_sql, {"upload_id": upload_id})
    rule_cols = list(cursor.keys())
    all_rules: List[Dict[str, Any]] = [dict(zip(rule_cols, row)) for row in cursor.fetchall()]

    if not all_rules:
        return _empty_workbook()

    # Optionally filter by commission type
    if commission_type_filter:
        all_rules = [r for r in all_rules if r.get("commission_type") == commission_type_filter]

    rule_ids = [r["id"] for r in all_rules]

    # ── 2. Fetch slabs for all rules in one query ──────────────────────────────
    slab_sql = text("""
        SELECT commission_rule_id, payin_type, premium_type, slab_from, slab_to,
               payin_od, payin_tp, payin_net, condition_field, "operator", value, original_text
        FROM slab_details
        WHERE commission_rule_id = ANY(:ids)
        ORDER BY commission_rule_id, slab_from ASC NULLS LAST
    """)
    slab_cursor = db.execute(slab_sql, {"ids": rule_ids})
    slab_cols = list(slab_cursor.keys())
    slabs_by_rule: Dict[int, List[Dict]] = {}
    for row in slab_cursor.fetchall():
        s = dict(zip(slab_cols, row))
        slabs_by_rule.setdefault(s["commission_rule_id"], []).append(s)

    # ── 3. Split into non-slab / slab buckets ─────────────────────────────────
    non_slab_rules = [r for r in all_rules if r.get("commission_type") != "SLAB"]
    slab_rules     = [r for r in all_rules if r.get("commission_type") == "SLAB"]

    # ── 4. Build workbook (shared with ORM path) ───────────────────────────────
    buffer = BytesIO()
    wb = xlsxwriter.Workbook(buffer, {
        "in_memory": True,
        "strings_to_numbers": False,
        "strings_to_urls": False,
    })

    # Shared formats
    FMT_HEADER = wb.add_format({
        "bold": True, "font_color": "#FFFFFF", "bg_color": "#4F46E5",
        "align": "center", "valign": "vcenter", "text_wrap": True,
        "border": 1, "border_color": "#4F46E5",
    })
    FMT_NORMAL     = wb.add_format({"valign": "top", "text_wrap": True, "border": 1, "border_color": "#CCCCCC"})
    FMT_DEFAULTED  = wb.add_format({"font_color": "#6D28D9", "valign": "top", "text_wrap": True, "border": 1, "border_color": "#CCCCCC"})
    FMT_SLAB_NRM   = wb.add_format({"align": "center", "valign": "vcenter", "text_wrap": True, "border": 1, "border_color": "#CCCCCC"})
    FMT_SLAB_DEF   = wb.add_format({"font_color": "#6D28D9", "align": "center", "valign": "vcenter", "text_wrap": True, "border": 1, "border_color": "#CCCCCC"})
    FMT_BIZ_NRM    = wb.add_format({"valign": "top", "text_wrap": True, "border": 1, "border_color": "#CCCCCC"})
    FMT_BIZ_DEF    = wb.add_format({"font_color": "#6D28D9", "valign": "top", "text_wrap": True, "border": 1, "border_color": "#CCCCCC"})
    FMT_SLAB_SEP   = wb.add_format({"align": "center", "valign": "vcenter", "text_wrap": True, "top": 1, "top_color": "#CCCCCC", "left": 1, "left_color": "#CCCCCC", "right": 1, "right_color": "#CCCCCC", "bottom": 2, "bottom_color": "#4F46E5"})
    FMT_BIZ_SEP    = wb.add_format({"valign": "top", "text_wrap": True, "top": 1, "top_color": "#CCCCCC", "left": 1, "left_color": "#CCCCCC", "right": 1, "right_color": "#CCCCCC", "bottom": 2, "bottom_color": "#4F46E5"})

    n_biz = len(BUSINESS_COLUMNS)

    # ── Non-Slab Sheet ─────────────────────────────────────────────────────────
    ns_headers = [label for label, _ in BUSINESS_COLUMNS] + [label for label, _ in NON_SLAB_RATE_COLUMNS]
    ws_ns = wb.add_worksheet("Non-Slab")
    ws_ns.freeze_panes(1, 0)
    for col_idx, label in enumerate(ns_headers):
        ws_ns.write(0, col_idx, label, FMT_HEADER)
    ns_widths = [len(h) for h in ns_headers]

    for row_idx, rule in enumerate(non_slab_rules, start=1):
        data = _serialize_rule_dict(rule, [], db)
        defaulted = set(data.get("_defaulted_fields") or [])
        row_vals = [data.get(f) for _, f in BUSINESS_COLUMNS] + [data.get(f) for _, f in NON_SLAB_RATE_COLUMNS]
        for col_idx, val in enumerate(row_vals):
            s = str(val) if val is not None else ""
            if len(s) > ns_widths[col_idx]:
                ns_widths[col_idx] = len(s)
            if col_idx < n_biz:
                _, field = BUSINESS_COLUMNS[col_idx]
                fmt = FMT_DEFAULTED if field in defaulted else FMT_NORMAL
            else:
                fmt = FMT_NORMAL
            ws_ns.write(row_idx, col_idx, val if val is not None else "", fmt)

    for col_idx, w in enumerate(ns_widths):
        ws_ns.set_column(col_idx, col_idx, _col_width(w))

    # ── Slab Sheet ─────────────────────────────────────────────────────────────
    sl_headers = [label for label, _ in BUSINESS_COLUMNS] + [label for label, _ in SLAB_TIER_COLUMNS]
    n_tier = len(SLAB_TIER_COLUMNS)
    ws_sl = wb.add_worksheet("Slab")
    ws_sl.freeze_panes(1, 0)
    for col_idx, label in enumerate(sl_headers):
        ws_sl.write(0, col_idx, label, FMT_HEADER)
    sl_widths = [len(h) for h in sl_headers]

    current_row = 1
    for rule in slab_rules:
        r_slabs = slabs_by_rule.get(rule["id"], [])
        data = _serialize_rule_dict(rule, r_slabs, db)
        defaulted = set(data.get("_defaulted_fields") or [])
        slabs = data.get("slabs") or [{}]
        biz_vals = [data.get(f) for _, f in BUSINESS_COLUMNS]
        first_tier_row = current_row
        n_tiers = len(slabs)

        for tier_idx, slab in enumerate(slabs):
            slab_vals = [slab.get(f) for _, f in SLAB_TIER_COLUMNS]
            slab_defaulted = set(slab.get("_defaulted_fields") or [])
            is_last = (tier_idx == n_tiers - 1)

            if tier_idx == 0:
                for col_idx, (_, field) in enumerate(BUSINESS_COLUMNS):
                    val = biz_vals[col_idx]
                    s = str(val) if val is not None else ""
                    if len(s) > sl_widths[col_idx]:
                        sl_widths[col_idx] = len(s)
                    fmt = FMT_BIZ_SEP if is_last else (FMT_BIZ_DEF if field in defaulted else FMT_BIZ_NRM)
                    ws_sl.write(current_row, col_idx, val if val is not None else "", fmt)
            elif is_last:
                for col_idx in range(n_biz):
                    ws_sl.write(current_row, col_idx, "", FMT_BIZ_SEP)

            for col_idx, (_, field) in enumerate(SLAB_TIER_COLUMNS):
                abs_col = n_biz + col_idx
                val = slab_vals[col_idx]
                s = str(val) if val is not None else ""
                if len(s) > sl_widths[abs_col]:
                    sl_widths[abs_col] = len(s)
                fmt = FMT_SLAB_SEP if is_last else (FMT_SLAB_DEF if field in slab_defaulted else FMT_SLAB_NRM)
                ws_sl.write(current_row, abs_col, val if val is not None else "", fmt)

            current_row += 1

        last_tier_row = current_row - 1
        if n_tiers > 1:
            for col_idx, (_, field) in enumerate(BUSINESS_COLUMNS):
                val = biz_vals[col_idx]
                fmt = FMT_BIZ_DEF if field in defaulted else FMT_BIZ_NRM
                ws_sl.merge_range(first_tier_row, col_idx, last_tier_row, col_idx,
                                  val if val is not None else "", fmt)

    for col_idx, w in enumerate(sl_widths):
        ws_sl.set_column(col_idx, col_idx, _col_width(w))

    wb.close()
    buffer.seek(0)
    return buffer


def _empty_workbook() -> BytesIO:
    """Return a minimal empty workbook when there are no rules to export."""
    buf = BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    wb.add_worksheet("Non-Slab")
    wb.add_worksheet("Slab")
    wb.close()
    buf.seek(0)
    return buf
