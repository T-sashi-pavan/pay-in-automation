from datetime import date, datetime
from typing import Any, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.commission_rule import CommissionRule
from backend.app.models.slab_detail import SlabDetail
from backend.app.models.rule_audit_log import RuleAuditLog
from backend.app.services.rule_serializer import serialize_commission_rule
from backend.app.services.validator.validator import RuleValidator

router = APIRouter(prefix="/api")


class FieldUpdateRequest(BaseModel):
    field: str
    value: Any = None
    edited_by: Optional[str] = None


# field name (as sent by the frontend) -> (model column attr, max length or None, required)
TEXT_FIELDS = {
    "lob": ("lob", 255, True),
    "file_type": ("file_type", 255, False),
    "insurance_company": ("insurance_company", 255, True),
    "product": ("product", 500, True),
    "policy_type": ("policy_type", 255, True),
    "plan_type": ("plan_type", 255, False),
    "sub_product": ("sub_product", 255, False),
    "class": ("class_", 255, False),
    "sub_class": ("sub_class", 255, False),
    "make": ("make", 255, False),
    "model": ("model", 255, False),
    "fuel_type": ("fuel_type", 255, False),
    "body_type": ("body_type", 255, False),
    "cpa_status": ("cpa_status", 255, False),
    "ncb_status": ("ncb_status", 255, False),
    "partner_type": ("partner_type", 255, False),
    "zone": ("zone", 255, False),
    "source": ("source", 255, False),
    "rto": ("rto", 500, False),
    "remarks": ("remarks", None, False),
}

# All 10 rate columns still exist on the model and the commission_type
# cascade keeps moving/nulling them for data consistency, but only the
# payin_* fields are directly user-editable — payout is always computed as
# 80% of payin at serialization time (see field_normalizer.compute_payout),
# so editing it directly would have no lasting effect.
RATE_FIELDS = [
    "payin_od", "payout_od", "payin_tp", "payout_tp",
    "payin_net", "payout_net", "payin_reward", "payout_reward",
    "payin_scheme", "payout_scheme",
]
EDITABLE_RATE_FIELDS = ["payin_od", "payin_tp", "payin_net", "payin_reward", "payin_scheme"]

SLAB_RATE_PCT_FIELDS = ["payin_od", "payout_od", "payin_tp", "payout_tp", "payin_net", "payout_net"]
EDITABLE_SLAB_RATE_FIELDS = ["payin_od", "payin_tp", "payin_net"]

FIELD_LABELS = {
    "lob": "LOB",
    "insurance_company": "Insurer",
    "product": "Product",
    "policy_type": "Policy Type",
    "state": "State",
    "vehicle_age_from": "Vehicle Age From",
    "vehicle_age_to": "Vehicle Age To",
    "effective_date": "Effective Date",
    "commission_type": "Commission Type",
    "slab_from": "Slab From",
    "slab_to": "Slab To",
    "payin_type": "Pay-In Type",
    "premium_type": "Premium Type",
}


def _label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " ").title())


PASSTHROUGH_STATE_PHRASES = ("except", "rest of")
PASSTHROUGH_STATE_VALUES = {"ALL", "PAN INDIA", "PAN_INDIA", "PAN", "ALL, INDIA", "PAN, INDIA", "ALL, PAN INDIA"}


def _validate_state(value: Any) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return "State cannot be empty."
    lower = str(value).lower()
    if any(p in lower for p in PASSTHROUGH_STATE_PHRASES) or str(value).strip().upper() in PASSTHROUGH_STATE_VALUES:
        return None
    for token in [t.strip() for t in str(value).split(",") if t.strip()]:
        if token.upper() not in RuleValidator.STANDARD_STATES:
            return f"Invalid State: '{token}'."
    return None


def _validate_rate(value: Any, label: str) -> Tuple[Optional[float], Optional[str]]:
    if value is None or str(value).strip() == "":
        return None, None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None, f"{label} must be a number."
    if v < 0 or v > 5:
        return None, f"{label} must be between 0% and 500%."
    return v, None


def _validate_bound(value: Any, label: str) -> Tuple[Optional[float], Optional[str]]:
    """For slab_from/slab_to — premium/volume boundaries, not percentages."""
    if value is None or str(value).strip() == "":
        return None, None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None, f"{label} must be a number."
    if v < 0:
        return None, f"{label} cannot be negative."
    return v, None


def _validate_int(value: Any, label: str) -> Tuple[Optional[int], Optional[str]]:
    if value is None or str(value).strip() == "":
        return None, None
    try:
        return int(float(value)), None
    except (TypeError, ValueError):
        return None, f"{label} must be a whole number."


def _validate_date(value: Any, label: str) -> Tuple[Optional[date], Optional[str]]:
    if value is None or str(value).strip() == "":
        return None, None
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date(), None
    except ValueError:
        return None, f"{label} must be a valid date (YYYY-MM-DD)."


def _write_audit(db: Session, commission_rule_id: int, field: str, old_value: Any, new_value: Any, edited_by: str) -> None:
    db.add(RuleAuditLog(
        commission_rule_id=commission_rule_id,
        field=field,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        edited_by=edited_by or "User",
    ))


def _apply_commission_type_change(db: Session, rule: CommissionRule, raw_new_type: Any, edited_by: str) -> None:
    new_type = str(raw_new_type).strip().upper().replace("-", "_") if raw_new_type else None
    if new_type not in ("SLAB", "NON_SLAB"):
        raise HTTPException(status_code=422, detail="Commission Type must be either SLAB or NON_SLAB.")

    old_type = rule.commission_type
    if old_type == new_type:
        return

    if new_type == "SLAB":
        if len(rule.slabs) > 0:
            raise HTTPException(
                status_code=409,
                detail="Cannot convert to Slab: this rule already has slab rows (data integrity issue — resolve manually)."
            )
        old_rates = {f: getattr(rule, f) for f in RATE_FIELDS}
        slab = SlabDetail(
            payin_type="PERCENTAGE",
            premium_type=None,
            slab_from=None,
            slab_to=None,
            payin_od=old_rates["payin_od"],
            payout_od=old_rates["payout_od"],
            payin_tp=old_rates["payin_tp"],
            payout_tp=old_rates["payout_tp"],
            payin_net=old_rates["payin_net"],
            payout_net=old_rates["payout_net"],
        )
        rule.slabs.append(slab)

        for f in RATE_FIELDS:
            if old_rates[f] is not None:
                setattr(rule, f, None)
                _write_audit(db, rule.id, f, old_rates[f], None, edited_by)

        rule.commission_type = "SLAB"
        rule.slab_configuration = True
        _write_audit(db, rule.id, "commission_type", old_type, "SLAB", edited_by)
        _write_audit(db, rule.id, "slab_configuration", False, True, edited_by)

    else:  # -> NON_SLAB
        if len(rule.slabs) == 0:
            raise HTTPException(
                status_code=409,
                detail="Cannot convert to Non-Slab: this rule has no slab rows (data integrity issue — resolve manually)."
            )
        if len(rule.slabs) > 1:
            raise HTTPException(
                status_code=400,
                detail="This rule has multiple slab tiers — edit or remove tiers individually before converting to Non-Slab."
            )

        slab = rule.slabs[0]
        moved = {
            "payin_od": slab.payin_od, "payout_od": slab.payout_od,
            "payin_tp": slab.payin_tp, "payout_tp": slab.payout_tp,
            "payin_net": slab.payin_net, "payout_net": slab.payout_net,
        }
        for f, v in moved.items():
            old_val = getattr(rule, f)
            setattr(rule, f, v)
            if old_val != v:
                _write_audit(db, rule.id, f, old_val, v, edited_by)

        if slab.slab_from is not None or slab.slab_to is not None:
            _write_audit(db, rule.id, "slab_from (discarded)", slab.slab_from, None, edited_by)
            _write_audit(db, rule.id, "slab_to (discarded)", slab.slab_to, None, edited_by)

        rule.slabs.remove(slab)
        db.delete(slab)
        rule.commission_type = "NON_SLAB"
        rule.slab_configuration = False
        _write_audit(db, rule.id, "commission_type", old_type, "NON_SLAB", edited_by)
        _write_audit(db, rule.id, "slab_configuration", True, False, edited_by)


@router.patch("/commission-rule/{rule_id}")
def update_commission_rule_field(rule_id: int, payload: FieldUpdateRequest, db: Session = Depends(get_db)):
    # Lock the row for the duration of the edit — no joinedload here, since
    # SELECT ... FOR UPDATE cannot be combined with an outer join in Postgres.
    rule = db.query(CommissionRule).filter(CommissionRule.id == rule_id).with_for_update().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Commission rule not found.")

    field = payload.field
    value = payload.value
    edited_by = payload.edited_by or "User"

    if field == "commission_type":
        _apply_commission_type_change(db, rule, value, edited_by)
    elif field == "state":
        error = _validate_state(value)
        if error:
            raise HTTPException(status_code=422, detail=error)
        old = rule.state
        new_value = str(value).strip() if value else None
        if old != new_value:
            rule.state = new_value
            _write_audit(db, rule.id, "state", old, new_value, edited_by)
    elif field in TEXT_FIELDS:
        column_attr, max_len, required = TEXT_FIELDS[field]
        label = _label(field)
        str_value = str(value).strip() if value is not None else ""
        if required and str_value == "":
            raise HTTPException(status_code=422, detail=f"{label} cannot be empty.")
        if max_len and len(str_value) > max_len:
            raise HTTPException(status_code=422, detail=f"{label} exceeds maximum length of {max_len} characters.")
        old = getattr(rule, column_attr)
        new_value = str_value if str_value != "" else None
        if old != new_value:
            setattr(rule, column_attr, new_value)
            _write_audit(db, rule.id, field, old, new_value, edited_by)
    elif field in ("vehicle_age_from", "vehicle_age_to"):
        new_value, error = _validate_int(value, _label(field))
        if error:
            raise HTTPException(status_code=422, detail=error)
        old = getattr(rule, field)
        if old != new_value:
            setattr(rule, field, new_value)
            _write_audit(db, rule.id, field, old, new_value, edited_by)
    elif field == "effective_date":
        new_value, error = _validate_date(value, "Effective Date")
        if error:
            raise HTTPException(status_code=422, detail=error)
        old = rule.effective_date
        if old != new_value:
            rule.effective_date = new_value
            _write_audit(db, rule.id, field, old, new_value, edited_by)
    elif field in EDITABLE_RATE_FIELDS:
        new_value, error = _validate_rate(value, _label(field))
        if error:
            raise HTTPException(status_code=422, detail=error)
        old = getattr(rule, field)
        if old != new_value:
            setattr(rule, field, new_value)
            _write_audit(db, rule.id, field, old, new_value, edited_by)
    else:
        raise HTTPException(status_code=400, detail=f"Field '{field}' is not editable.")

    db.commit()
    db.refresh(rule)
    return serialize_commission_rule(rule, db)


@router.patch("/slab-detail/{slab_id}")
def update_slab_detail_field(slab_id: int, payload: FieldUpdateRequest, db: Session = Depends(get_db)):
    slab = db.query(SlabDetail).filter(SlabDetail.id == slab_id).with_for_update().first()
    if not slab:
        raise HTTPException(status_code=404, detail="Slab detail not found.")

    field = payload.field
    value = payload.value
    edited_by = payload.edited_by or "User"
    label = _label(field)

    if field in ("payin_type", "premium_type"):
        str_value = str(value).strip() if value is not None else ""
        if len(str_value) > 50:
            raise HTTPException(status_code=422, detail=f"{label} exceeds maximum length of 50 characters.")
        old = getattr(slab, field)
        new_value = str_value if str_value != "" else None
        if old != new_value:
            setattr(slab, field, new_value)
            _write_audit(db, slab.commission_rule_id, f"slab[{slab.id}].{field}", old, new_value, edited_by)
    elif field in ("slab_from", "slab_to"):
        new_value, error = _validate_bound(value, label)
        if error:
            raise HTTPException(status_code=422, detail=error)
        old = getattr(slab, field)
        if old != new_value:
            setattr(slab, field, new_value)
            _write_audit(db, slab.commission_rule_id, f"slab[{slab.id}].{field}", old, new_value, edited_by)
    elif field in EDITABLE_SLAB_RATE_FIELDS:
        new_value, error = _validate_rate(value, label)
        if error:
            raise HTTPException(status_code=422, detail=error)
        old = getattr(slab, field)
        if old != new_value:
            setattr(slab, field, new_value)
            _write_audit(db, slab.commission_rule_id, f"slab[{slab.id}].{field}", old, new_value, edited_by)
    else:
        raise HTTPException(status_code=400, detail=f"Field '{field}' is not editable.")

    db.commit()
    db.refresh(slab.rule)
    return serialize_commission_rule(slab.rule, db)
