from backend.app.services.excel_parser.parser import extract_numeric_range, ExcelParserService

def test_extract_numeric_range_upto_returns_one():
    # 'upto X' must start at 1.0, not 0.0
    slab_from, slab_to = extract_numeric_range("upto 180")
    assert slab_from == 1.0
    assert slab_to == 180.0

def test_slab_start_normalization_on_merge():
    # If merged slabs have a start of 0.0, they should be normalized to 1.0
    parser = ExcelParserService()
    
    raw_rules = [
        {
            "lob": "Motor",
            "file_type": "New",
            "insurance_company": "Shriram",
            "product": "Two Wheeler",
            "policy_type": "Comprehensive",
            "commission_type": "SLAB",
            "slabs": [
                {
                    "payin_type": "PERCENTAGE",
                    "premium_type": "OD",
                    "slab_from": 0.0,  # 0.0 should become 1.0
                    "slab_to": 150.0,
                    "payin_od": 10.0,
                    "payout_od": 8.0,
                }
            ]
        }
    ]
    
    merged = parser._group_and_merge_rules(raw_rules)
    assert len(merged) == 1
    slab = merged[0]["slabs"][0]
    assert slab["slab_from"] == 1.0

def test_slab_deduplication():
    # Slabs with identical ranges and rates should be collapsed
    parser = ExcelParserService()
    
    # 2 rows that are identical in business keys and slab parameters
    raw_rules = [
        {
            "lob": "Motor", "file_type": "New", "insurance_company": "Shriram", "product": "Two Wheeler",
            "policy_type": "Comprehensive", "commission_type": "SLAB",
            "slabs": [{"payin_type": "PERCENTAGE", "premium_type": "OD", "slab_from": 1.0, "slab_to": 150.0, "payin_od": 10.0}]
        },
        {
            "lob": "Motor", "file_type": "New", "insurance_company": "Shriram", "product": "Two Wheeler",
            "policy_type": "Comprehensive", "commission_type": "SLAB",
            "slabs": [{"payin_type": "PERCENTAGE", "premium_type": "OD", "slab_from": 1.0, "slab_to": 150.0, "payin_od": 10.0}]
        }
    ]
    
    merged = parser._group_and_merge_rules(raw_rules)
    assert len(merged) == 1
    assert len(merged[0]["slabs"]) == 1
