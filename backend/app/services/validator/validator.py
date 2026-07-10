from typing import Dict, Any, List, Set, Tuple

class RuleValidator:
    # Standard Indian State Codes
    STANDARD_STATES: Set[str] = {
        "AP", "AR", "AS", "BR", "CG", "CT", "GA", "GJ", "HR", "HP", "JH", "KA", "KL", "MP", 
        "MH", "MN", "ML", "MZ", "NL", "OD", "OR", "PB", "RJ", "SK", "TN", "TG", "TS", "TR", 
        "UP", "UK", "UA", "UT", "WB", "AN", "CH", "DN", "DD", "DL", "JK", "LA", "LD", "PY", "ALL"
    }

    @staticmethod
    def validate_rule(rule_data: Dict[str, Any], existing_keys: Set[Tuple]) -> Tuple[str, List[str]]:
        """
        Validates normalized rule data.
        Returns a tuple of (status, warnings_list)
        where status is 'VALID' (only minor/auto-corrected warning flags) or 'WARNING' (critical actions needed).
        """
        critical_warnings = []
        non_critical_warnings = []
        
        # 1. Check required fields (CRITICAL)
        required_fields = {
            "lob": "Line of Business (LOB)",
            "insurance_company": "Insurance Company",
            "product": "Product",
            "policy_type": "Policy Type"
        }
        for field, label in required_fields.items():
            val = rule_data.get(field)
            if val is None or str(val).strip() == "" or str(val).strip().upper() in ("N/A", "NONE", "UNKNOWN"):
                critical_warnings.append(f"Missing mandatory field: {label}")

        # 2. Check invalid states (NON-CRITICAL)
        state_str = rule_data.get("state")
        if state_str:
            state_lower = state_str.lower()
            # Skip negative lists and PAN India wildcards from invalid state warnings
            if "except" in state_lower or "rest of" in state_lower or state_str in ("ALL", "PAN INDIA", "PAN_INDIA", "PAN", "ALL, INDIA", "PAN, INDIA", "ALL, PAN INDIA"):
                pass
            else:
                states = [s.strip() for s in state_str.split(",") if s.strip()]
                for s in states:
                    if s not in RuleValidator.STANDARD_STATES:
                        non_critical_warnings.append(f"Invalid state code: '{s}'")

        # 3. Check invalid dates (NON-CRITICAL - auto-corrected to upload date)
        effective_date = rule_data.get("effective_date")
        if not effective_date:
            non_critical_warnings.append("Missing or invalid effective date (Defaulted to upload date)")

        # 4. Check duplicate keys (NON-CRITICAL)
        rule_key = (
            rule_data.get("lob"),
            rule_data.get("insurance_company"),
            rule_data.get("product"),
            rule_data.get("policy_type"),
            rule_data.get("plan_type"),
            rule_data.get("sub_product"),
            rule_data.get("state"),
            rule_data.get("rto"),
            rule_data.get("make"),
            rule_data.get("model"),
            rule_data.get("vehicle_age_from"),
            rule_data.get("vehicle_age_to")
        )
        if rule_key in existing_keys:
            non_critical_warnings.append("Duplicate row detected in the workbook")
        else:
            existing_keys.add(rule_key)

        # Set status to WARNING only if there are critical warnings
        status = "WARNING" if critical_warnings else "VALID"
        all_warnings = critical_warnings + non_critical_warnings
        return status, all_warnings
