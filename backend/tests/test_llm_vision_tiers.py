"""
Covers the correctness bugs found in the LLM-vision PDF extraction path
(_llm_row_to_rule / _tiers_to_slabs in pdf_parser/parser.py):
- premium_type must always be OD/TP/NET, never a made-up "DISCOUNT %" label.
- Combined-rate tiers (e.g. "30% OD + 90% TP") split into two rows sharing
  one slab_from/slab_to boundary, matching the established one-rate-bucket-
  per-row convention used by every real Excel-sourced slab.
- Touching tier boundaries get normalized to non-overlapping ranges.
- check_duplicate_slab_ranges flags genuine duplicates and unresolved
  (null/null) boundary pile-ups, without false-flagging a legitimate
  same-range OD/TP pair.
"""
from backend.app.services.pdf_parser.parser import PdfParserService
from backend.app.services.excel_parser.parser import check_duplicate_slab_ranges

svc = PdfParserService()


def test_combined_od_tp_tier_splits_into_two_rows_with_valid_premium_type():
    tiers = [
        {"discount_from_pct": 0, "discount_to_pct": 40, "commission_od_pct": 30, "commission_tp_pct": 90, "commission_net_pct": None},
        {"discount_from_pct": 40, "discount_to_pct": 70, "commission_od_pct": 25, "commission_tp_pct": 85, "commission_net_pct": None},
        {"discount_from_pct": 70, "discount_to_pct": None, "commission_od_pct": 20, "commission_tp_pct": 80, "commission_net_pct": None},
    ]
    slabs = svc._tiers_to_slabs(tiers)

    assert len(slabs) == 6, "3 tiers x 2 rate buckets (OD, TP) each = 6 rows"
    for slab in slabs:
        assert slab["premium_type"] in ("OD", "TP", "NET"), "premium_type must never be a made-up label like 'DISCOUNT %'"


def test_touching_boundaries_become_non_overlapping():
    tiers = [
        {"discount_from_pct": 0, "discount_to_pct": 40, "commission_od_pct": 30, "commission_tp_pct": None, "commission_net_pct": None},
        {"discount_from_pct": 40, "discount_to_pct": 70, "commission_od_pct": 25, "commission_tp_pct": None, "commission_net_pct": None},
        {"discount_from_pct": 70, "discount_to_pct": None, "commission_od_pct": 20, "commission_tp_pct": None, "commission_net_pct": None},
    ]
    slabs = svc._tiers_to_slabs(tiers)
    ranges = [(s["slab_from"], s["slab_to"]) for s in slabs]

    assert ranges == [(0, 40), (41, 70), (71, None)], "adjacent touching bounds must be bumped by 1, not left overlapping"


def test_pure_net_tier_produces_one_row_per_tier():
    tiers = [
        {"discount_from_pct": 0, "discount_to_pct": 60, "commission_od_pct": None, "commission_tp_pct": None, "commission_net_pct": 5},
        {"discount_from_pct": 60, "discount_to_pct": None, "commission_od_pct": None, "commission_tp_pct": None, "commission_net_pct": 2.5},
    ]
    slabs = svc._tiers_to_slabs(tiers)

    assert len(slabs) == 2
    assert all(s["premium_type"] == "NET" for s in slabs)
    assert [s["payin_net"] for s in slabs] == [5, 2.5]


def test_od_tp_pair_sharing_a_range_is_not_flagged_as_duplicate():
    tiers = [
        {"discount_from_pct": 0, "discount_to_pct": 40, "commission_od_pct": 30, "commission_tp_pct": 90, "commission_net_pct": None},
    ]
    slabs = svc._tiers_to_slabs(tiers)

    assert check_duplicate_slab_ranges(slabs) == []


def test_exact_duplicate_range_and_premium_type_is_flagged():
    slabs = [
        {"slab_from": 0, "slab_to": 40, "premium_type": "OD"},
        {"slab_from": 0, "slab_to": 40, "premium_type": "OD"},
    ]
    warnings = check_duplicate_slab_ranges(slabs)

    assert len(warnings) == 1
    assert "Duplicate slab range" in warnings[0]


def test_multiple_null_boundary_tiers_are_flagged_even_though_not_exact_duplicates():
    # This is the "every slab row becomes 1-500000" symptom — the underlying
    # slab_from/slab_to are both null (extraction failed), which the display
    # layer then paints identically, looking like a duplicate to the user.
    slabs = [
        {"slab_from": None, "slab_to": None, "premium_type": "OD"},
        {"slab_from": None, "slab_to": None, "premium_type": "TP"},
    ]
    warnings = check_duplicate_slab_ranges(slabs)

    assert len(warnings) == 1
    assert "unresolved boundary" in warnings[0]
