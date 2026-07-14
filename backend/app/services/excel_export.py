from typing import Any, Dict, List
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy.orm import Session

from backend.app.models.commission_rule import CommissionRule
from backend.app.services.rule_serializer import serialize_commission_rule

# Column order shared by both sheets — matches the field-by-field spec this
# app normalizes every rule against (see field_normalizer.py/rule_serializer.py).
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

SLAB_TIER_COLUMNS: List[tuple] = [
    ("Pay-In Type", "payin_type"), ("Premium Type", "premium_type"),
    ("Slab From", "slab_from"), ("Slab Upto", "slab_to"),
    ("Pay-In OD", "payin_od"), ("Pay-Out OD", "payout_od"),
    ("Pay-In TP", "payin_tp"), ("Pay-Out TP", "payout_tp"),
    ("Pay-In Net", "payin_net"), ("Pay-Out Net", "payout_net"),
]

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
DEFAULTED_FONT = Font(color="6D28D9")  # purple-700 — flags a business-default value, not a real extracted one
PARENT_ROW_FONT = Font(bold=True)
PARENT_ROW_FILL = PatternFill(start_color="EEF2FF", end_color="EEF2FF", fill_type="solid")


def _style_header_row(ws, row_idx: int = 1) -> None:
    for cell in ws[row_idx]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL


def _autosize_columns(ws) -> None:
    for col in ws.columns:
        max_len = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 2, 10), 60)


def build_export_workbook(rules: List[CommissionRule], db: Session) -> BytesIO:
    """
    Generates a two-sheet .xlsx (Non-Slab, Slab) from the FULL filtered set of
    CommissionRule ORM objects — not the paginated page the browser happens to
    have loaded. Reuses serialize_commission_rule so exported values match
    exactly what the UI shows (including business defaults like "ALL"/"NA"),
    and flags any defaulted (non-real) cell in orange via `_defaulted_fields`
    the same serializer already reports.
    """
    non_slab_rules = [r for r in rules if r.commission_type != "SLAB"]
    slab_rules = [r for r in rules if r.commission_type == "SLAB"]

    wb = Workbook()

    ws_ns = wb.active
    ws_ns.title = "Non-Slab"
    ws_ns.append([label for label, _ in BUSINESS_COLUMNS] + [label for label, _ in NON_SLAB_RATE_COLUMNS])
    _style_header_row(ws_ns)
    for rule in non_slab_rules:
        data = serialize_commission_rule(rule, db)
        defaulted = set(data.get("_defaulted_fields") or [])
        row_values = [data.get(field) for _, field in BUSINESS_COLUMNS] + [data.get(field) for _, field in NON_SLAB_RATE_COLUMNS]
        ws_ns.append(row_values)
        excel_row = ws_ns.max_row
        for col_idx, (_, field) in enumerate(BUSINESS_COLUMNS, start=1):
            if field in defaulted:
                ws_ns.cell(row=excel_row, column=col_idx).font = DEFAULTED_FONT
    _autosize_columns(ws_ns)

    ws_sl = wb.create_sheet("Slab")
    all_columns = [label for label, _ in BUSINESS_COLUMNS] + [label for label, _ in SLAB_TIER_COLUMNS]
    ws_sl.append(all_columns)
    _style_header_row(ws_sl)
    business_col_count = len(BUSINESS_COLUMNS)
    for rule in slab_rules:
        data = serialize_commission_rule(rule, db)
        defaulted = set(data.get("_defaulted_fields") or [])
        business_values = [data.get(field) for _, field in BUSINESS_COLUMNS]

        slabs = data.get("slabs") or []
        if slabs:
            first_slab = slabs[0]
            first_slab_values = [first_slab.get(field) for _, field in SLAB_TIER_COLUMNS]
            ws_sl.append(business_values + first_slab_values)
            parent_row = ws_sl.max_row
            
            for col_idx, (_, field) in enumerate(BUSINESS_COLUMNS, start=1):
                cell = ws_sl.cell(row=parent_row, column=col_idx)
                cell.font = DEFAULTED_FONT if field in defaulted else PARENT_ROW_FONT
                cell.fill = PARENT_ROW_FILL
                
            first_slab_defaulted = set(first_slab.get("_defaulted_fields") or [])
            for col_idx, (_, field) in enumerate(SLAB_TIER_COLUMNS, start=business_col_count + 1):
                cell = ws_sl.cell(row=parent_row, column=col_idx)
                cell.fill = PARENT_ROW_FILL
                if field in first_slab_defaulted:
                    cell.font = DEFAULTED_FONT

            for slab in slabs[1:]:
                slab_defaulted = set(slab.get("_defaulted_fields") or [])
                tier_values = [None] * business_col_count + [slab.get(field) for _, field in SLAB_TIER_COLUMNS]
                ws_sl.append(tier_values)
                tier_row = ws_sl.max_row
                ws_sl.row_dimensions[tier_row].outline_level = 1
                for col_idx, (_, field) in enumerate(SLAB_TIER_COLUMNS, start=business_col_count + 1):
                    if field in slab_defaulted:
                        ws_sl.cell(row=tier_row, column=col_idx).font = DEFAULTED_FONT
        else:
            ws_sl.append(business_values + [None] * len(SLAB_TIER_COLUMNS))
            parent_row = ws_sl.max_row
            for col_idx, (_, field) in enumerate(BUSINESS_COLUMNS, start=1):
                cell = ws_sl.cell(row=parent_row, column=col_idx)
                cell.font = DEFAULTED_FONT if field in defaulted else PARENT_ROW_FONT
                cell.fill = PARENT_ROW_FILL
            for col_idx in range(business_col_count + 1, business_col_count + len(SLAB_TIER_COLUMNS) + 1):
                ws_sl.cell(row=parent_row, column=col_idx).fill = PARENT_ROW_FILL

    ws_sl.sheet_properties.outlinePr.summaryBelow = False
    _autosize_columns(ws_sl)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
