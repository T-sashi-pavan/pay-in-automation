from backend.app.services.normalizer.normalizer import ValueNormalizer

def test_normalize_vehicle_age():
    # Ranges
    assert ValueNormalizer.normalize_vehicle_age("5-10 YEARS") == (5, 10)
    assert ValueNormalizer.normalize_vehicle_age("3 TO 5") == (3, 5)
    # Upto scenarios
    assert ValueNormalizer.normalize_vehicle_age("UPTO 5 YEARS") == (0, 5)
    assert ValueNormalizer.normalize_vehicle_age("<= 3") == (0, 3)
    # Above scenarios
    assert ValueNormalizer.normalize_vehicle_age("5+") == (5, 99)
    assert ValueNormalizer.normalize_vehicle_age("> 3 YEARS") == (3, 99)
    # Single values
    assert ValueNormalizer.normalize_vehicle_age(5) == (5, 5)

def test_normalize_states():
    assert ValueNormalizer.normalize_states("AP,TS,TN") == "AP, TS, TN"
    assert ValueNormalizer.normalize_states("AP / TS / TN") == "AP, TS, TN"
    assert ValueNormalizer.normalize_states("AP;TS;TN") == "AP, TS, TN"
    # New coverage
    assert ValueNormalizer.normalize_states("ANDHRA PRADESH") == "AP"
    assert ValueNormalizer.normalize_states("HARYANA ( HR RTO ONLY)") == "HR"
    assert ValueNormalizer.normalize_states("ALL EXCEPT (DL, MP, CG)") == "ALL EXCEPT DL, MP, CG"
    # Misspellings and spacing variations
    assert ValueNormalizer.normalize_states("FOR THE STATE OF TAMIL NADU") == "TN"
    assert ValueNormalizer.normalize_states("TAMILNADU & PONDICHERRY") == "TN, PY"
    assert ValueNormalizer.normalize_states("ALL ALL VALIDITY EXCEPT FOR THE STATES OF UTTAR PRADESH, MADHYA PRADESH AND TAMIL NADU") == "ALL EXCEPT UP, MP, TN"
    assert ValueNormalizer.normalize_states("ALL ALL EXCEPT FOR THE STATES OF MADHYA PRADESH AND AS") == "ALL EXCEPT MP, AS"
    assert ValueNormalizer.normalize_states("PAN INDIA VALIDITY") == "ALL"


def test_normalize_percentage():
    assert ValueNormalizer.normalize_percentage("15%") == 15.0
    assert ValueNormalizer.normalize_percentage("15.5 %") == 15.5
    assert ValueNormalizer.normalize_percentage(12.5) == 12.5

def test_custom_regions_normalization():
    assert ValueNormalizer.normalize_states("ROM1") == "ROM1"
    assert ValueNormalizer.normalize_states("ROM2") == "ROM2"
    assert ValueNormalizer.normalize_states("ROM3") == "ROM3"
    assert ValueNormalizer.normalize_states("Hyderabad") == "HYDERABAD"
    assert ValueNormalizer.normalize_states("Chennai") == "CHENNAI"
    assert ValueNormalizer.normalize_states("Bangalore") == "BANGALORE"
    assert ValueNormalizer.normalize_states("Corporate Region") == "CORPORATE REGION"
    assert ValueNormalizer.normalize_states("Branch Region") == "BRANCH REGION"
    assert ValueNormalizer.normalize_states("Regional Office") == "REGIONAL OFFICE"

def test_split_merging_and_policy_type():
    from backend.app.services.excel_parser.parser import ExcelParserService
    parser = ExcelParserService()
    
    # 3 rules: 
    # - Jharkhand Comp CD1 = 60%
    # - Jharkhand Comp CD2 = 40%
    # - Jharkhand TP CD2 = 35%
    raw_rules = [
        {
            "lob": "Motor", "file_type": "ALL", "insurance_company": "Digit",
            "product": "GCV3", "policy_type": "Comprehensive", "state": "JH",
            "payin_od": 0.60, "remarks": "Column: Jharkhand - Comp - CD1", "raw_json": {"Jharkhand - Comp - CD1": 0.60}
        },
        {
            "lob": "Motor", "file_type": "ALL", "insurance_company": "Digit",
            "product": "GCV3", "policy_type": "Comprehensive", "state": "JH",
            "payin_od": 0.40, "remarks": "Column: Jharkhand - Comp - CD2", "raw_json": {"Jharkhand - Comp - CD2": 0.40}
        },
        {
            "lob": "Motor", "file_type": "ALL", "insurance_company": "Digit",
            "product": "GCV3", "policy_type": "Third Party", "state": "JH",
            "payin_tp": 0.35, "remarks": "Column: Jharkhand - TP - CD2", "raw_json": {"Jharkhand - TP - CD2": 0.35}
        }
    ]
    
    merged = parser._group_and_merge_rules(raw_rules)
    
    # We expect 2 merged rules: one for CD1, one for CD2.
    assert len(merged) == 2
    
    # Identify which is which
    cd1_rule = next(r for r in merged if "CD1" in r["remarks"])
    cd2_rule = next(r for r in merged if "CD2" in r["remarks"])
    
    assert cd1_rule["payin_od"] == 0.60
    assert cd1_rule["payin_tp"] is None
    assert cd1_rule["policy_type"] == "Comprehensive"
    assert "_traceability" in cd1_rule["raw_json"]
    assert cd1_rule["raw_json"]["_traceability"]["original_column"] == "Jharkhand - Comp - CD1"
    
    assert cd2_rule["payin_od"] == 0.40
    assert cd2_rule["payin_tp"] == 0.35
    assert cd2_rule["policy_type"] == "Comprehensive, Third Party"
    assert "_traceability" in cd2_rule["raw_json"]
    assert cd2_rule["raw_json"]["_traceability"]["original_column"] in ("Jharkhand - Comp - CD2", "Jharkhand - TP - CD2")
    
    # Check explanation warnings are generated
    assert any("separate CRM rows" in w for w in cd1_rule["warnings"])
    assert any("separate CRM rows" in w for w in cd2_rule["warnings"])
    assert any("Policy Type became" in w for w in cd2_rule["warnings"])
