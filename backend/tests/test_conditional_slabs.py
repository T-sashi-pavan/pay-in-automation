import pytest
from backend.app.services.excel_parser.parser import parse_tiered_rate_text, check_duplicate_slab_ranges

def test_parse_tiered_rate_text_conditional():
    # Test operator '='
    res = parse_tiered_rate_text("Age 0: 5%")
    assert res is None  # Should be None if less than 2 segments
    
    # Test operator '>=' and '='
    res = parse_tiered_rate_text("Age 0: 5%\nAge >=1: 17.5%")
    assert res is not None
    assert len(res) == 2
    
    # First tier
    assert res[0]["condition_field"] == "Vehicle Age"
    assert res[0]["operator"] == "="
    assert res[0]["value"] == 0.0
    assert res[0]["slab_from"] == 0.0
    assert res[0]["slab_to"] == 0.0
    assert res[0]["rate_pct"] == 5.0
    
    # Second tier
    assert res[1]["condition_field"] == "Vehicle Age"
    assert res[1]["operator"] == ">="
    assert res[1]["value"] == 1.0
    assert res[1]["slab_from"] == 1.0
    assert res[1]["slab_to"] is None
    assert res[1]["rate_pct"] == 17.5

def test_parse_tiered_rate_text_range_and_plus():
    res = parse_tiered_rate_text("Upto 0-2 Yrs - 30%\n3+ Yrs - 37.5%")
    assert res is not None
    assert len(res) == 2
    
    # First tier (normal range)
    assert res[0]["operator"] is None
    assert res[0]["slab_from"] == 0.0
    assert res[0]["slab_to"] == 2.0
    assert res[0]["rate_pct"] == 30.0
    
    # Second tier (plus)
    assert res[1]["operator"] == ">="
    assert res[1]["value"] == 3.0
    assert res[1]["slab_from"] == 3.0
    assert res[1]["slab_to"] is None
    assert res[1]["rate_pct"] == 37.5

def test_slab_validation():
    # Slabs with From > To (e.g. 1 -> 0)
    slabs = [
        {"slab_from": 1.0, "slab_to": 0.0, "premium_type": "OD"},
        {"slab_from": 1.0, "slab_to": "OPEN", "premium_type": "OD"}
    ]
    warnings = check_duplicate_slab_ranges(slabs)
    assert any("limit (1.0) is greater than" in w for w in warnings)
    
    # Overlapping slabs (e.g. 0-2 and 1-OPEN)
    slabs_overlap = [
        {"slab_from": 0.0, "slab_to": 2.0, "premium_type": "OD"},
        {"slab_from": 1.0, "slab_to": "OPEN", "premium_type": "OD"}
    ]
    warnings_overlap = check_duplicate_slab_ranges(slabs_overlap)
    assert any("Overlapping slab range detected" in w for w in warnings_overlap)
