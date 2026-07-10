import os
import json
from typing import Dict, List, Optional

class ColumnMapper:
    def __init__(self, config_path: Optional[str] = None):
        if not config_path:
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
        
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
        except Exception:
            self.config = {"mappings": {}}
            
        self.mappings = self.config.get("mappings", {})

    def normalize_string(self, val: str) -> str:
        if not val or not isinstance(val, str):
            return ""
        # Convert to lower, strip whitespace, and normalize common delimiters
        return val.strip().lower().replace("_", " ").replace("-", " ")

    def resolve_headers(self, headers: List[str]) -> Dict[str, str]:
        """
        Maps standard field names to actual Excel headers.
        Returns a dictionary mapping: { standard_field: actual_excel_header }
        """
        resolved = {}
        normalized_headers = {self.normalize_string(str(h)): h for h in headers if h is not None}

        for standard_field, aliases in self.mappings.items():
            for alias in aliases:
                norm_alias = self.normalize_string(alias)
                if norm_alias in normalized_headers:
                    resolved[standard_field] = normalized_headers[norm_alias]
                    break  # Found mapped column, stop checking aliases

        return resolved
