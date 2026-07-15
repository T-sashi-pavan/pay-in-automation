import logging
import re
from typing import Dict, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.master_data import (
    MasterState, MasterProduct, MasterVehicleType, MasterPolicyType,
)

logger = logging.getLogger(__name__)

# Small, effectively-static reference tables — loaded once per process instead
# of queried on every request/row.
_cache: Dict[str, Dict[str, str]] = {}


def clear_cache() -> None:
    """Used by tests / after seeding to force a reload on next access."""
    _cache.clear()


def _load_table(db: Session, model, cache_key: str) -> Dict[str, str]:
    if cache_key not in _cache:
        try:
            rows = db.query(model).all()
            _cache[cache_key] = {row.code.strip().upper(): row.name for row in rows}
        except SQLAlchemyError:
            # Defensive: if the master-tables migration hasn't been applied yet,
            # expansion is skipped entirely rather than breaking every existing
            # page that renders a CommissionRule (this lookup is purely additive).
            db.rollback()
            logger.warning("Master table '%s' unavailable (migration not applied?) — skipping expansion.", cache_key)
            _cache[cache_key] = {}
    return _cache[cache_key]


def get_state_map(db: Session) -> Dict[str, str]:
    return _load_table(db, MasterState, "states")


def get_product_map(db: Session) -> Dict[str, str]:
    return _load_table(db, MasterProduct, "products")


def get_vehicle_type_map(db: Session) -> Dict[str, str]:
    return _load_table(db, MasterVehicleType, "vehicle_types")


def get_policy_type_map(db: Session) -> Dict[str, str]:
    return _load_table(db, MasterPolicyType, "policy_types")


def expand_state(raw: Optional[str], db: Session) -> Optional[str]:
    """
    Best-effort expansion of a (possibly comma-separated) state value.
    Returns None (caller should fall back to the raw value) if nothing matched.
    """
    if not raw or not str(raw).strip():
        return None
    state_map = get_state_map(db)
    tokens = [t.strip() for t in str(raw).split(",")]
    expanded = []
    changed = False
    for token in tokens:
        mapped = state_map.get(token.upper())
        if mapped:
            if mapped not in expanded:
                expanded.append(mapped)
            changed = True
        else:
            if token not in expanded:
                expanded.append(token)
    return ", ".join(expanded) if changed else None


def expand_product(raw: Optional[str], db: Session) -> Optional[str]:
    """
    Best-effort whole-word expansion of known product-code abbreviations
    embedded in a free-text product string (e.g. "GCCV LCV 2001-2800 GVW").
    Candidates are tried longest-code-first so e.g. "GCCV" is substituted
    before "GCV" is tried against the same text, avoiding GCV-inside-GCCV
    corruption. Returns None if nothing matched.
    """
    if not raw or not str(raw).strip():
        return None
    product_map = get_product_map(db)
    if not product_map:
        return None

    result = str(raw)
    changed = False
    for code in sorted(product_map.keys(), key=len, reverse=True):
        pattern = re.compile(r'\b' + re.escape(code) + r'\b', re.IGNORECASE)
        if pattern.search(result):
            result = pattern.sub(product_map[code], result)
            changed = True

    return result if changed else None
