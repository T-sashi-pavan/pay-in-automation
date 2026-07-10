from backend.app.services.validator.validator import RuleValidator

def test_rule_validator():
    # Valid rule scenario
    rule_1 = {
        "lob": "Motor",
        "insurance_company": "ICICI",
        "product": "Car Insurance",
        "policy_type": "Comprehensive",
        "state": "AP, TS",
        "effective_date": "2026-07-09"
    }
    
    existing_keys = set()
    status, warnings = RuleValidator.validate_rule(rule_1, existing_keys)
    assert status == "VALID"
    assert len(warnings) == 0

    # Missing mandatory fields scenario (CRITICAL - WARNING status)
    rule_2 = {
        "lob": "",
        "insurance_company": "ICICI",
        "product": "Car Insurance",
        "policy_type": "",
        "state": "AP, TS",
        "effective_date": "2026-07-09"
    }
    status, warnings = RuleValidator.validate_rule(rule_2, existing_keys)
    assert status == "WARNING"
    assert "Missing mandatory field: Line of Business (LOB)" in warnings
    assert "Missing mandatory field: Policy Type" in warnings

    # Invalid state scenario (NON-CRITICAL - VALID status)
    rule_3 = {
        "lob": "Motor",
        "insurance_company": "ICICI",
        "product": "Car Insurance",
        "policy_type": "Comprehensive",
        "state": "AP, XX, TS",
        "effective_date": "2026-07-09"
    }
    status, warnings = RuleValidator.validate_rule(rule_3, existing_keys)
    assert status == "VALID"
    assert "Invalid state code: 'XX'" in warnings

    # Duplicate row scenario (NON-CRITICAL - VALID status)
    rule_4 = {
        "lob": "Motor",
        "insurance_company": "ICICI",
        "product": "Car Insurance",
        "policy_type": "Comprehensive",
        "state": "AP, TS",
        "effective_date": "2026-07-09"
    }
    # Since rule_1 has been validated and added to existing_keys, rule_4 should flag as duplicate
    status, warnings = RuleValidator.validate_rule(rule_4, existing_keys)
    assert status == "VALID"
    assert "Duplicate row detected in the workbook" in warnings
