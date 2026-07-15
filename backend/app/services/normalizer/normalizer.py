import re
from datetime import datetime, date, timedelta
from typing import Optional, Tuple

def extract_commission_column(header: str, state_str: str) -> str:
    if not header:
        return ""
    h_clean = header.lower()
    
    # 1. Remove state/region names
    if state_str:
        for token in state_str.split(","):
            token_clean = token.strip().lower()
            if token_clean:
                h_clean = h_clean.replace(token_clean, "")
                
    # Also remove common state names from the header
    for loc_name in ["jharkhand", "bihar", "west bengal", "orissa", "gujarat", "goa", "delhi", "kerala", "rajasthan", "uttar pradesh", "punjab", "jammu", "srinagar", "tamil nadu", "assam", "bangalore", "karnataka", "uttarakhand", "haryana", "himachal pradesh", "andamans", "nagaland"]:
        h_clean = h_clean.replace(loc_name, "")
        
    # 2. Remove premium type keywords
    for kw in ["comp", "pack", "act", "saod", "satp", "tp", "od", "net"]:
        h_clean = re.sub(r'\b' + re.escape(kw) + r'\b', "", h_clean)
        
    # 3. Clean up extra spaces and non-alphanumeric characters
    h_clean = re.sub(r'[^a-z0-9]', " ", h_clean)
    words = [w.strip() for w in h_clean.split() if w.strip()]
    
    return " ".join(words).upper()


def merge_non_conflicting_rules(rules: list) -> list:
    merged_list = []
    for r in rules:
        merged_success = False
        for m in merged_list:
            conflict = False
            rate_fields = [
                "payin_od", "payout_od", "payin_tp", "payout_tp",
                "payin_net", "payout_net", "payin_reward", "payout_reward",
                "payin_scheme", "payout_scheme"
            ]
            for rf in rate_fields:
                if m.get(rf) is not None and r.get(rf) is not None and m.get(rf) != r.get(rf):
                    conflict = True
                    break
            
            if not conflict:
                # Merge r into m
                for rf in rate_fields:
                    if r.get(rf) is not None:
                        m[rf] = r[rf]
                
                # Merge policy type
                p1 = m.get("policy_type") or "ALL"
                p2 = r.get("policy_type") or "ALL"
                p_types = {pt.strip() for pt in (p1.split(",") + p2.split(",")) if pt.strip() and pt.upper() != "ALL"}
                m["policy_type"] = ", ".join(sorted(list(p_types))) if p_types else "ALL"
                
                # Merge remarks
                rem1 = m.get("remarks") or ""
                rem2 = r.get("remarks") or ""
                rems = []
                for rem in (rem1.split(" | ") + rem2.split(" | ")):
                    if rem.strip() and rem.strip() not in rems:
                        rems.append(rem.strip())
                m["remarks"] = " | ".join(rems) if rems else "ALL"
                
                # Merge raw_json
                if isinstance(m.get("raw_json"), dict) and isinstance(r.get("raw_json"), dict):
                    m["raw_json"].update(r["raw_json"])
                    
                # Merge warnings
                w1 = m.get("warnings") or []
                w2 = r.get("warnings") or []
                m["warnings"] = list(set(w1 + w2))
                
                merged_success = True
                break
        
        if not merged_success:
            merged_list.append(r.copy())
    return merged_list


def add_traceability_to_rule(r: dict):
    remarks = r.get("remarks") or ""
    header_name = ""
    if "Column: " in remarks:
        parts = remarks.split("Column: ")
        header_name = parts[-1].split(" | ")[0].strip()
    
    orig_header = r.get("state") or "ALL"
    orig_col = header_name or "ALL"
    orig_cell = header_name or "ALL"
    
    rate_val = None
    if header_name and r.get("raw_json"):
        rate_val = r["raw_json"].get(header_name)
    elif r.get("raw_json"):
        for k, v in r["raw_json"].items():
            if k not in ["Segment", "Make", "Carrier Type", "PROD", "SUBCLASS", "MODEL"]:
                rate_val = v
                orig_col = k
                orig_cell = k
                break
                
    orig_comm_text = f"{orig_col} = {rate_val}" if rate_val is not None else orig_col
    
    traceability = {
        "original_header": orig_header,
        "original_column": orig_col,
        "original_cell": orig_cell,
        "original_commission_text": orig_comm_text
    }
    
    if "raw_json" not in r or r["raw_json"] is None:
        r["raw_json"] = {}
    r["raw_json"]["_traceability"] = traceability


def patched_group_and_merge_rules(self, all_parsed_rules: list) -> list:
    from backend.app.services.excel_parser.parser import check_duplicate_slab_ranges
    
    # 1. Clean policy types and add comm_col & traceability
    for r in all_parsed_rules:
        add_traceability_to_rule(r)
        
        # Pre-correct column classifications (ACT/TP keywords prioritized over parent OD headers)
        remarks = r.get("remarks") or ""
        header_name = ""
        if "Column: " in remarks:
            parts = remarks.split("Column: ")
            header_name = parts[-1].split(" | ")[0].strip()
            
        if header_name:
            h_clean = re.sub(r'[^a-z0-9]', " ", header_name.lower())
            words = h_clean.split()
            if any(w in words for w in ["tp", "satp", "act"]):
                # Move flat rates if incorrectly put under OD
                if r.get("payin_od") is not None and r.get("payin_tp") is None:
                    r["payin_tp"] = r["payin_od"]
                    r["payin_od"] = None
                    r["policy_type"] = "Third Party"
                # Move payout rates
                if r.get("payout_od") is not None and r.get("payout_tp") is None:
                    r["payout_tp"] = r["payout_od"]
                    r["payout_od"] = None
                
                # Move slab rates if any
                if r.get("slabs"):
                    for s in r["slabs"]:
                        if s.get("payin_od") is not None and s.get("payin_tp") is None:
                            s["payin_tp"] = s["payin_od"]
                            s["payin_od"] = None
                            s["premium_type"] = "TP"
                        if s.get("payout_od") is not None and s.get("payout_tp") is None:
                            s["payout_tp"] = s["payout_od"]
                            s["payout_od"] = None
        
        # Ensure policy type is inferred if missing
        if not r.get("policy_type") or r["policy_type"] == "ALL":
            if r.get("payin_od") is not None and r.get("payin_tp") is not None:
                r["policy_type"] = "Comprehensive, Third Party"
            elif r.get("payin_od") is not None:
                r["policy_type"] = "Comprehensive"
            elif r.get("payin_tp") is not None:
                r["policy_type"] = "Third Party"
            else:
                r["policy_type"] = "ALL"

    # Group rules by (business_key, comm_col)
    grouped_by_business_col = {}
    business_key_to_cols = {}
    
    for r in all_parsed_rules:
        b_key = (
            str(r.get("lob") or "").strip().upper(),
            str(r.get("file_type") or "").strip().upper(),
            str(r.get("insurance_company") or "").strip().upper(),
            str(r.get("product") or "").strip().upper(),
            str(r.get("plan_type") or "").strip().upper(),
            str(r.get("sub_product") or "").strip().upper(),
            str(r.get("class") or "").strip().upper(),
            str(r.get("sub_class") or "").strip().upper(),
            str(r.get("make") or "").strip().upper(),
            str(r.get("model") or "").strip().upper(),
            str(r.get("fuel_type") or "").strip().upper(),
            str(r.get("body_type") or "").strip().upper(),
            str(r.get("vehicle_age_from") or "").strip(),
            str(r.get("vehicle_age_to") or "").strip(),
            str(r.get("cpa_status") or "").strip().upper(),
            str(r.get("ncb_status") or "").strip().upper(),
            str(r.get("partner_type") or "").strip().upper(),
            str(r.get("state") or "").strip().upper(),
            str(r.get("zone") or "").strip().upper(),
            str(r.get("source") or "").strip().upper(),
            str(r.get("rto") or "").strip().upper(),
            str(r.get("effective_date") or "").strip(),
        )
        
        remarks = r.get("remarks") or ""
        header_name = ""
        if "Column: " in remarks:
            parts = remarks.split("Column: ")
            header_name = parts[-1].split(" | ")[0].strip()
        comm_col = extract_commission_column(header_name, r.get("state"))
        
        grouped_by_business_col.setdefault((b_key, comm_col), []).append(r)
        business_key_to_cols.setdefault(b_key, set()).add(comm_col)

    final_rules = []
    for (b_key, comm_col), group in grouped_by_business_col.items():
        is_any_slab = any(r.get("commission_type") == "SLAB" for r in group)
        
        if is_any_slab:
            base_rule = group[0].copy()
            base_rule["commission_type"] = "SLAB"
            base_rule["slab_configuration"] = True
            
            merged_slabs = []
            for rule_item in group:
                if rule_item.get("slabs"):
                    merged_slabs.extend(rule_item["slabs"])
                else:
                    slab_obj = {
                        "payin_type": "PERCENTAGE",
                        "premium_type": None,
                        "slab_from": None,
                        "slab_to": None,
                        "payin_od": rule_item.get("payin_od"),
                        "payout_od": rule_item.get("payout_od"),
                        "payin_tp": rule_item.get("payin_tp"),
                        "payout_tp": rule_item.get("payout_tp"),
                        "payin_net": rule_item.get("payin_net"),
                        "payout_net": rule_item.get("payout_net")
                    }
                    merged_slabs.append(slab_obj)
            
            unique_slabs = []
            seen_slab_keys = set()
            for s in merged_slabs:
                s_key = (
                    s.get("slab_from"),
                    s.get("slab_to"),
                    s.get("payin_od"),
                    s.get("payin_tp"),
                    s.get("payin_net"),
                )
                if s_key not in seen_slab_keys:
                    seen_slab_keys.add(s_key)
                    unique_slabs.append(s)
            base_rule["slabs"] = unique_slabs
            
            for rf in ("payin_od", "payout_od", "payin_tp", "payout_tp", "payin_net", "payout_net",
                      "payin_reward", "payout_reward", "payin_scheme", "payout_scheme"):
                base_rule[rf] = None
                
            p_types = set()
            for ri in group:
                p = ri.get("policy_type") or "ALL"
                for pt in p.split(","):
                    if pt.strip() and pt.strip().upper() != "ALL":
                        p_types.add(pt.strip())
            base_rule["policy_type"] = ", ".join(sorted(list(p_types))) if p_types else "ALL"
            
            all_rems = []
            combined_raw = {}
            for ri in group:
                for rem in (ri.get("remarks") or "").split(" | "):
                    if rem.strip() and rem.strip() not in all_rems:
                        all_rems.append(rem.strip())
                if isinstance(ri.get("raw_json"), dict):
                    combined_raw.update(ri["raw_json"])
            base_rule["remarks"] = " | ".join(all_rems) if all_rems else "ALL"
            base_rule["raw_json"] = combined_raw
            
            dup_warnings = check_duplicate_slab_ranges(unique_slabs)
            base_rule["warnings"] = list(base_rule.get("warnings") or [])
            if dup_warnings:
                base_rule["warnings"].extend(dup_warnings)
                base_rule["validation_status"] = "WARNING"
                
            final_rules.append(base_rule)
        else:
            merged_group = merge_non_conflicting_rules(group)
            final_rules.extend(merged_group)

    for r in final_rules:
        b_key = (
            str(r.get("lob") or "").strip().upper(),
            str(r.get("file_type") or "").strip().upper(),
            str(r.get("insurance_company") or "").strip().upper(),
            str(r.get("product") or "").strip().upper(),
            str(r.get("plan_type") or "").strip().upper(),
            str(r.get("sub_product") or "").strip().upper(),
            str(r.get("class") or "").strip().upper(),
            str(r.get("sub_class") or "").strip().upper(),
            str(r.get("make") or "").strip().upper(),
            str(r.get("model") or "").strip().upper(),
            str(r.get("fuel_type") or "").strip().upper(),
            str(r.get("body_type") or "").strip().upper(),
            str(r.get("vehicle_age_from") or "").strip(),
            str(r.get("vehicle_age_to") or "").strip(),
            str(r.get("cpa_status") or "").strip().upper(),
            str(r.get("ncb_status") or "").strip().upper(),
            str(r.get("partner_type") or "").strip().upper(),
            str(r.get("state") or "").strip().upper(),
            str(r.get("zone") or "").strip().upper(),
            str(r.get("source") or "").strip().upper(),
            str(r.get("rto") or "").strip().upper(),
            str(r.get("effective_date") or "").strip(),
        )
        
        cols = business_key_to_cols.get(b_key, set())
        
        rate_fields = [
            "payin_od", "payout_od", "payin_tp", "payout_tp",
            "payin_net", "payout_net", "payin_reward", "payout_reward",
            "payin_scheme", "payout_scheme"
        ]
        for rf in rate_fields:
            if rf not in r:
                r[rf] = None

        if "warnings" not in r or r["warnings"] is None:
            r["warnings"] = []
            
        if len(cols) > 1:
            clean_cols = sorted(list([c for c in cols if c]))
            col_list_str = ", ".join(clean_cols) if clean_cols else "different commission columns"
            r["warnings"].append(f"Merged because all business attributes matched except commission columns. Generated separate CRM rows for {col_list_str} to avoid data loss.")
            
        p_type = r.get("policy_type") or "ALL"
        if "," in p_type:
            r["warnings"].append(f"Policy Type became '{p_type}' instead of 'ALL' because multiple policy types were merged for this rule.")

    return final_rules


class ValueNormalizer:
    def __init__(self):
        self._apply_patches()

    def _apply_patches(self):
        try:
            from backend.app.services.excel_parser.parser import ExcelParserService, STATES_LIST, STATE_ABBR_MAP
            ExcelParserService._group_and_merge_rules = patched_group_and_merge_rules
            
            new_states = ["chennai", "corporate region", "branch region", "regional office"]
            for s in new_states:
                if s not in STATES_LIST:
                    STATES_LIST.append(s)
                    
            new_mappings = {
                "rom1": "ROM1",
                "rom2": "ROM2",
                "rom3": "ROM3",
                "rom": "ROM",
                "hyderabad": "HYDERABAD",
                "chennai": "CHENNAI",
                "bangalore": "BANGALORE",
                "corporate region": "CORPORATE REGION",
                "branch region": "BRANCH REGION",
                "regional office": "REGIONAL OFFICE",
                "tg": "TS",
                "ts": "TS",
                "telangana": "TS",
                "telengana": "TS",
                "ap/ts": "AP, TS"
            }
            for k, v in new_mappings.items():
                STATE_ABBR_MAP[k] = v
        except Exception:
            pass

    @staticmethod
    def normalize_vehicle_age(age_val) -> Tuple[Optional[int], Optional[int]]:
        """
        Normalizes vehicle age strings to a (from_age, to_age) integer tuple.
        E.g. "UPTO 5 YEARS" -> (0, 5)
             "5-10 YEARS" -> (5, 10)
             "> 3 YEARS" -> (3, 99)
        """
        if age_val is None or age_val == "":
            return None, None
        
        # If already numerical
        if isinstance(age_val, (int, float)):
            val = int(age_val)
            return val, val

        age_str = str(age_val).upper().strip()

        # Try range format: e.g. "3-5 YEARS", "3 TO 5", "3 - 5"
        range_match = re.search(r"(\d+)\s*(?:-|TO)\s*(\d+)", age_str)
        if range_match:
            return int(range_match.group(1)), int(range_match.group(2))
            
        # Try "UPTO 5" or "UP TO 5" or "<= 5" or "BELOW 5" or "UNDER 5" or "NEW"
        upto_match = re.search(r"(?:UP\s*TO|UNDER|BELOW|NEW|<=|<|=)\s*(\d+)", age_str)
        if upto_match:
            return 0, int(upto_match.group(1))
            
        # Try "ABOVE 5" or "> 5" or "5+" or "5 YEARS AND ABOVE"
        above_match = re.search(r"(?:ABOVE|>|\+)\s*(\d+)|(\d+)\s*(?:\+|AND\s*ABOVE|&\s*ABOVE)", age_str)
        if above_match:
            val = above_match.group(1) or above_match.group(2)
            return int(val), 99  # 99 represents open end age
            
        # Try single number: e.g. "5 YEARS"
        single_match = re.search(r"(\d+)", age_str)
        if single_match:
            val = int(single_match.group(1))
            return val, val
            
        return None, None

    @staticmethod
    def normalize_states(state_val) -> Optional[str]:
        """
        Normalizes variations of state string lists to standard state abbreviations.
        """
        if state_val is None or state_val == "":
            return None
        
        state_str = str(state_val).strip()
        
        # 1. Strip parenthetical blocks containing "RTO" or "ONLY" (case-insensitive)
        state_str = re.sub(r"\([^)]*(?:RTO|ONLY)[^)]*\)", "", state_str, flags=re.IGNORECASE).strip()
        state_str = state_str.strip(", ")
        
        if not state_str:
            return None

        # Clean duplicate "ALL ALL" -> "ALL"
        state_str = re.sub(r"\bALL\s+ALL\b", "ALL", state_str, flags=re.IGNORECASE)
        # Clean "VALIDITY" or other boilerplate words if they are right next to ALL
        state_str = re.sub(r"\bALL\s+VALIDITY\b", "ALL", state_str, flags=re.IGNORECASE)

        # State abbreviation mapping dictionary
        state_fullname_map = {
            "andhra pradesh": "AP", "andra pradesh": "AP", "andhrapradesh": "AP", "andrapradesh": "AP",
            "arunachal pradesh": "AR", "arunachalpradesh": "AR",
            "assam": "AS", "bihar": "BR", "chandigarh": "CH", "chhattisgarh": "CG", "chattisgarh": "CG",
            "delhi": "DL", "ncr": "DL", "goa": "GA", "gujarat": "GJ", "haryana": "HR",
            "himachal pradesh": "HP", "himachalpradesh": "HP", "himachal": "HP",
            "jammu & kashmir": "JK", "jammu and kashmir": "JK", "jammu & kasmir": "JK", "j&k": "JK", "j & k": "JK", "jammu": "JK",
            "jharkhand": "JH", "karnataka": "KA", "kerala": "KL", "ladakh": "LA",
            "madhya pradesh": "MP", "madhyapradesh": "MP", "maharashtra": "MH", "manipur": "MN",
            "meghalaya": "ML", "mizoram": "MZ", "nagaland": "NL", "odisha": "OD",
            "orissa": "OD", "puducherry": "PY", "pondicherry": "PY", "pondy": "PY", "punjab": "PB",
            "andamans": "AN",
            "rajasthan": "RJ", "sikkim": "SK", "tamil nadu": "TN", "tamilnadu": "TN", "tripura": "TR",
            "uttar pradesh": "UP", "uttarpradesh": "UP", "uttarakhand": "UK", "uttaranchal": "UK",
            "west bengal": "WB", "westbengal": "WB", "telangana": "TS", "telengana": "TS",
            "rom1": "ROM1", "rom2": "ROM2", "rom3": "ROM3", "rom": "ROM",
            "hyderabad": "HYDERABAD", "chennai": "CHENNAI", "bangalore": "BANGALORE",
            "corporate region": "CORPORATE REGION", "branch region": "BRANCH REGION",
            "regional office": "REGIONAL OFFICE"
        }
        
        # Helper to find all states mentioned in a text
        def find_states_in_text(text: str) -> list[str]:
            text_lower = text.lower()
            
            # 1. Look for full state names and track their positions (with overlap protection)
            full_name_positions = []
            sorted_fullnames = sorted(state_fullname_map.keys(), key=len, reverse=True)
            matched_ranges = []
            for fullname in sorted_fullnames:
                abbr = state_fullname_map[fullname]
                for m in re.finditer(re.escape(fullname), text_lower):
                    start, end = m.start(), m.end()
                    # Check if this range overlaps with an already matched longer range
                    overlap = False
                    for ms, me in matched_ranges:
                        if not (end <= ms or start >= me):
                            overlap = True
                            break
                    if not overlap:
                        full_name_positions.append((start, abbr))
                        matched_ranges.append((start, end))
            
            # 2. Look for word-bounded abbreviations in the text and track positions
            abbr_positions = []
            abbrs = {"AP", "TS", "AR", "AS", "BR", "CH", "CG", "DL", "GA", "GJ", "HR", "HP", "JK", "JH", 
                     "KA", "KL", "LA", "MP", "MH", "MN", "ML", "MZ", "NL", "OD", "PY", "PB", "RJ", "SK", 
                     "TN", "TR", "UP", "UK", "WB", "ROM1", "ROM2", "ROM3", "ROM", "HYDERABAD", "CHENNAI",
                     "BANGALORE", "CORPORATE REGION", "BRANCH REGION", "REGIONAL OFFICE"}
            for m in re.finditer(r"\b[A-Za-z0-9_]+\b", text):
                word_upper = m.group(0).upper()
                if word_upper in abbrs:
                    # Check if this start position was already matched as a full state name to avoid duplicate matches
                    overlap = False
                    for ms, me in matched_ranges:
                        if m.start() >= ms and m.start() < me:
                            overlap = True
                            break
                    if not overlap:
                        abbr_positions.append((m.start(), word_upper))
            
            # Combine and sort by index of appearance in text
            all_positions = sorted(full_name_positions + abbr_positions, key=lambda x: x[0])
            
            # Deduplicate while preserving text order
            unique_found = []
            for _, abbr in all_positions:
                if abbr not in unique_found:
                    unique_found.append(abbr)
            return unique_found
            
            # Combine and sort by index of appearance in text
            all_positions = sorted(full_name_positions + abbr_positions, key=lambda x: x[0])
            
            # Deduplicate while preserving text order
            unique_found = []
            for _, abbr in all_positions:
                if abbr not in unique_found:
                    unique_found.append(abbr)
            return unique_found

        state_lower = state_str.lower()
        has_except = any(word in state_lower for word in ["except", "exclude", "excluding", "but not", "other than"])
        
        found_states = find_states_in_text(state_str)
        
        if has_except:
            if found_states:
                return f"ALL EXCEPT {', '.join(found_states)}"
            return "ALL"
        else:
            if found_states:
                return ", ".join(found_states)
            
            if "all" in state_lower or "india" in state_lower:
                return "ALL"
                
            return state_str.upper()

    @staticmethod
    def normalize_date(date_val) -> Optional[date]:
        """
        Normalizes common date representations to a python date object.
        """
        if date_val is None or date_val == "":
            return None
        if isinstance(date_val, (date, datetime)):
            return date_val.date() if isinstance(date_val, datetime) else date_val
            
        date_str = str(date_val).strip()
        # Remove time component if present
        if " " in date_str:
            date_str = date_str.split(" ")[0]

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Try Excel numerical date float
        try:
            float_days = float(date_str)
            # Excel start date is Dec 30, 1899
            return (datetime(1899, 12, 30) + timedelta(days=float_days)).date()
        except ValueError:
            pass

        return None

    @staticmethod
    def normalize_percentage(val) -> Optional[float]:
        """
        Normalizes a string/numeric percentage into a clean float.
        """
        if val is None or val == "":
            return None
        if isinstance(val, (int, float)):
            return float(val)
            
        val_str = str(val).strip().replace("%", "").strip()
        try:
            return float(val_str)
        except ValueError:
            return None
