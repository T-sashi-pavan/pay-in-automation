from typing import Any, Dict, List
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
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

# Slab tier detail columns — written once per slab row (vertical / CRM-Ready layout)
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

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
DEFAULTED_FONT = Font(color="6D28D9")  # purple-700 — flags a business-default, not a real extracted value
PARENT_ROW_FONT = Font(bold=True)
PARENT_ROW_FILL = PatternFill(start_color="EEF2FF", end_color="EEF2FF", fill_type="solid")

THIN_BORDER = Border(
    left=Side(style='thin', color='CCCCCC'),
    right=Side(style='thin', color='CCCCCC'),
    top=Side(style='thin', color='CCCCCC'),
    bottom=Side(style='thin', color='CCCCCC')
)

CENTER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
TOP_ALIGN = Alignment(vertical="top", wrap_text=True)


def _style_header_row(ws, row_idx: int = 1) -> None:
    for cell in ws[row_idx]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN


def _autosize_columns(ws) -> None:
    from openpyxl.utils import get_column_letter
    for col in ws.columns:
        max_len = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 60)


def build_export_workbook(rules: List[CommissionRule], db: Session) -> BytesIO:
    """
    Generates a two-sheet .xlsx (Non-Slab, Slab).

    Non-Slab sheet: one flat row per rule, business + rate columns.

    Slab sheet: CRM-Ready vertical merged-rows layout (matches Image 4).
        Single header row: [Business cols...] [Pay-In Type] [Premium Type]
                           [Payin Slab From] [Payin Slab To] [OD] [TP] [Net] [Payout OD] ...
        One data row per slab TIER, business columns merged vertically per rule.
    """
    non_slab_rules = [r for r in rules if r.commission_type != "SLAB"]
    slab_rules = [r for r in rules if r.commission_type == "SLAB"]

    wb = Workbook()

    # ── NON-SLAB SHEET ──────────────────────────────────────────────────────────
    ws_ns = wb.active
    ws_ns.title = "Non-Slab"
    ws_ns.append([label for label, _ in BUSINESS_COLUMNS] + [label for label, _ in NON_SLAB_RATE_COLUMNS])
    _style_header_row(ws_ns)
    ws_ns.freeze_panes = "A2"

    for rule in non_slab_rules:
        data = serialize_commission_rule(rule, db)
        defaulted = set(data.get("_defaulted_fields") or [])
        row_values = (
            [data.get(field) for _, field in BUSINESS_COLUMNS]
            + [data.get(field) for _, field in NON_SLAB_RATE_COLUMNS]
        )
        ws_ns.append(row_values)
        excel_row = ws_ns.max_row
        for col_idx, (_, field) in enumerate(BUSINESS_COLUMNS, start=1):
            if field in defaulted:
                ws_ns.cell(row=excel_row, column=col_idx).font = DEFAULTED_FONT

    for row in ws_ns.iter_rows(min_row=1, max_row=ws_ns.max_row, min_col=1, max_col=ws_ns.max_column):
        for cell in row:
            cell.border = THIN_BORDER

    _autosize_columns(ws_ns)

    # ── SLAB SHEET ──────────────────────────────────────────────────────────────
    # Layout (CRM-Ready / Image 4):
    #
    #   Row 1 — header: [Biz cols... | Pay-In Type | Premium Type | Slab From | Slab To | OD | TP | Net | ...]
    #   Row 2+ — one row per slab tier; business cells merged vertically for each rule block.
    #
    #   Example (2-tier rule):
    #     | Motor | ... | Column: GJ - Comp | PERCENTAGE | OD | 0    | 0    | 60% | - | - | ...
    #     |       |     |                   | PERCENTAGE | OD | 1    | OPEN | 85% | - | - | ...
    #     | Motor | ... | Column: MH - TP   | PERCENTAGE | TP | 0    | 0    | -   | 22| - | ...
    #
    ws_sl = wb.create_sheet("Slab")
    ws_sl.freeze_panes = "A2"

    n_biz = len(BUSINESS_COLUMNS)
    n_tier = len(SLAB_TIER_COLUMNS)
    total_cols = n_biz + n_tier

    # Single header row
    ws_sl.append(
        [label for label, _ in BUSINESS_COLUMNS]
        + [label for label, _ in SLAB_TIER_COLUMNS]
    )
    _style_header_row(ws_sl, row_idx=1)

    # Data rows
    for rule in slab_rules:
        data = serialize_commission_rule(rule, db)
        defaulted = set(data.get("_defaulted_fields") or [])
        slabs = data.get("slabs") or []

        if not slabs:
            slabs = [{}]  # at least one row per rule

        business_values = [data.get(field) for _, field in BUSINESS_COLUMNS]
        first_rule_row = ws_sl.max_row + 1

        for tier_idx, slab in enumerate(slabs):
            slab_values = [slab.get(field) for _, field in SLAB_TIER_COLUMNS]

            if tier_idx == 0:
                ws_sl.append(business_values + slab_values)
            else:
                # Business columns blank — will be merged with first_rule_row
                ws_sl.append([None] * n_biz + slab_values)

            excel_row = ws_sl.max_row

            # Style business column cells (first tier row only, others merged away)
            if tier_idx == 0:
                for col_idx, (_, field) in enumerate(BUSINESS_COLUMNS, start=1):
                    cell = ws_sl.cell(row=excel_row, column=col_idx)
                    cell.border = THIN_BORDER
                    cell.alignment = TOP_ALIGN
                    if field in defaulted:
                        cell.font = DEFAULTED_FONT

            # Style slab tier columns
            slab_defaulted = set(slab.get("_defaulted_fields") or [])
            for col_idx, (_, field) in enumerate(SLAB_TIER_COLUMNS, start=n_biz + 1):
                cell = ws_sl.cell(row=excel_row, column=col_idx)
                cell.border = THIN_BORDER
                cell.alignment = CENTER_ALIGN
                if field in slab_defaulted:
                    cell.font = DEFAULTED_FONT

        last_rule_row = ws_sl.max_row

        # Merge business columns vertically across all tier rows of this rule
        if last_rule_row > first_rule_row:
            for col_idx in range(1, n_biz + 1):
                ws_sl.merge_cells(
                    start_row=first_rule_row, start_column=col_idx,
                    end_row=last_rule_row, end_column=col_idx
                )
                ws_sl.cell(row=first_rule_row, column=col_idx).alignment = TOP_ALIGN

        # Medium bottom border = visual rule separator between different business rules
        for col_idx in range(1, total_cols + 1):
            ws_sl.cell(row=last_rule_row, column=col_idx).border = Border(
                left=Side(style='thin', color='CCCCCC'),
                right=Side(style='thin', color='CCCCCC'),
                top=Side(style='thin', color='CCCCCC'),
                bottom=Side(style='medium', color='4F46E5'),
            )

    _autosize_columns(ws_sl)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer

