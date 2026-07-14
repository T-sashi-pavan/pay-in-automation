import re
from datetime import datetime, date, timedelta
from typing import Optional, Tuple

class ValueNormalizer:
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

        # State abbreviation mapping dictionary
        state_map = {
            "andhra pradesh": "AP", "andra pradesh": "AP", "ap/ts": "AP, TS", "ap": "AP", "ts": "TS", 
            "tg": "TS", "telangana": "TS", "telengana": "TS", "arunachal": "AR", "arunachal pradesh": "AR", 
            "ar": "AR", "assam": "AS", "as": "AS", "bihar": "BR", "br": "BR", "bh": "BR", "chandigarh": "CH", "ch": "CH", 
            "chhattisgarh": "CG", "cg": "CG", "delhi": "DL", "dl": "DL", "ncr": "DL", "goa": "GA", "ga": "GA",
            "gujarat": "GJ", "gj": "GJ", "haryana": "HR", "hr": "HR", "himachal": "HP", "hp": "HP", 
            "jammu": "JK", "kashmir": "JK", "jk": "JK", "jharkhand": "JH", "jh": "JH", 
            "karnataka": "KA", "ka": "KA", "kerala": "KL", "kl": "KL", "ladakh": "LA", 
            "madhya pradesh": "MP", "mp": "MP", "maharashtra": "MH", "mh": "MH", "manipur": "MN", 
            "meghalaya": "ML", "ml": "ML", "mizoram": "MZ", "nagaland": "NL", "nl": "NL", "odisha": "OD", "orissa": "OD", 
            "od": "OD", "or": "OD", "puducherry": "PY", "pondicherry": "PY", "punjab": "PB", "pb": "PB", 
            "rajasthan": "RJ", "rj": "RJ", "sikkim": "SK", "tamil nadu": "TN", "tn": "TN", 
            "tripura": "TR", "tr": "TR", "uttar pradesh": "UP", "up": "UP", "uttarakhand": "UK", 
            "uk": "UK", "west bengal": "WB", "wb": "WB", "pan india": "ALL", "pan": "ALL", 
            "india": "ALL", "all": "ALL"
        }
        
        # 2. Check if this is a negative list expression (e.g. contains "except" or "rest of")
        state_lower = state_str.lower()
        if "except" in state_lower or "rest of" in state_lower:
            words = re.split(r"([,();/\s]+)", state_str)
            normalized_words = []
            for w in words:
                w_stripped = w.strip().lower()
                if w_stripped in state_map:
                    normalized_words.append(state_map[w_stripped])
                else:
                    normalized_words.append(w.upper() if w.isalpha() else w)
            return "".join(normalized_words)

        # 3. Standard comma/slash/semicolon/newline-separated parsing
        parts = re.split(r"[,/;\n]+", state_str)
        clean_parts = []
        for p in parts:
            p_clean = p.strip()
            if not p_clean:
                continue
            p_lower = p_clean.lower()
            
            # Map standard state name to standard abbreviation
            if p_lower in state_map:
                mapped = state_map[p_lower]
                # If mapped contains commas (e.g. "AP, TS"), split them
                for m in mapped.split(","):
                    clean_parts.append(m.strip())
            else:
                clean_parts.append(p_clean.upper())

        # Deduplicate while preserving order
        unique_parts = []
        for cp in clean_parts:
            if cp not in unique_parts:
                unique_parts.append(cp)

        if not unique_parts:
            return None
        return ", ".join(unique_parts)

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
