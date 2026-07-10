from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.services import master_data_service

router = APIRouter(prefix="/api/master")

_GETTERS = {
    "states": master_data_service.get_state_map,
    "products": master_data_service.get_product_map,
    "vehicle-types": master_data_service.get_vehicle_type_map,
    "policy-types": master_data_service.get_policy_type_map,
}


@router.get("/{kind}")
def get_master_list(kind: str, db: Session = Depends(get_db)):
    """
    Read-only lookup dictionaries (state/product/vehicle-type/policy-type
    code -> display name) for edit-popover autosuggest. These are reference
    data, not enums — editable fields stay free-text on the frontend.
    """
    getter = _GETTERS.get(kind)
    if not getter:
        raise HTTPException(status_code=404, detail=f"Unknown master list '{kind}'.")
    mapping = getter(db)
    return [{"code": code, "name": name} for code, name in sorted(mapping.items())]
