from typing import Any, Dict, List

from sqlalchemy.orm import Session

from backend.app.models.commission_rule import CommissionRule
from backend.app.services import master_data_service
from backend.app.services.field_normalizer import default_or, derive_plan_type, compute_payout, clean


def _serialize_slab(s) -> Dict[str, Any]:
    payin_od, payin_tp, payin_net = s.payin_od, s.payin_tp, s.payin_net

    defaulted_fields: List[str] = []
    if clean(s.payin_type) is None:
        defaulted_fields.append("payin_type")
    if clean(s.premium_type) is None:
        defaulted_fields.append("premium_type")
    if s.slab_from is None:
        defaulted_fields.append("slab_from")
    if s.slab_to is None:
        defaulted_fields.append("slab_to")

    return {
        "id": s.id,
        "payin_type": default_or(s.payin_type, "NET"),
        "premium_type": default_or(
            s.premium_type, "OD" if payin_od is not None else ("TP" if payin_tp is not None else "NET")
        ),
        "slab_from": s.slab_from if (s.slab_from is not None and s.slab_from != 0 and s.slab_from != 0.0) else 1,
        "slab_to": s.slab_to if s.slab_to is not None else 500000,
        "payin_od": payin_od,
        "payout_od": compute_payout(payin_od),
        "payin_tp": payin_tp,
        "payout_tp": compute_payout(payin_tp),
        "payin_net": payin_net,
        "payout_net": compute_payout(payin_net),
        "_defaulted_fields": defaulted_fields,
    }


def serialize_commission_rule(r: CommissionRule, db: Session) -> Dict[str, Any]:
    """
    Canonical response shape for a CommissionRule, reused by the existing
    GET /uploads/{id} and POST /search endpoints, the new PATCH endpoints,
    and the frontend table. Two kinds of transforms happen here, both
    display-time only — the underlying DB row (and what PATCH edits) is
    untouched:

    1. Field defaults: every free-text field that came back null/blank from
       the parser gets a business default ("ALL", "NA", "All Partners", or a
       numeric default for vehicle age) instead of surfacing as an empty
       cell — matching the CRM form's own field rules.
    2. Payout = 80% of payin, always computed here rather than read from a
       stored column — payout was never an independently-sourced value.

    `state_label`/`product_label` remain best-effort *additions* alongside
    the (now-defaulted) raw fields, same as before.

    `_defaulted_fields` lists every field key (matching this dict's own keys)
    whose value came back null/blank from the parser and got a business
    default here — i.e. "this cell is not a real extracted value." Consumers
    (frontend cell rendering, the .xlsx export in excel_export.py) use this to
    visually flag defaults instead of presenting them as indistinguishable
    from genuinely-extracted data.
    """
    payin_od, payin_tp, payin_net = r.payin_od, r.payin_tp, r.payin_net
    payin_reward, payin_scheme = r.payin_reward, r.payin_scheme

    defaulted_fields: List[str] = []
    for field_key, raw_value in (
        ("lob", r.lob), ("file_type", r.file_type), ("product", r.product),
        ("policy_type", r.policy_type), ("plan_type", r.plan_type), ("sub_product", r.sub_product),
        ("class", r.class_), ("sub_class", r.sub_class), ("make", r.make), ("model", r.model),
        ("fuel_type", r.fuel_type), ("body_type", r.body_type), ("cpa_status", r.cpa_status),
        ("ncb_status", r.ncb_status), ("partner_type", r.partner_type), ("state", r.state),
        ("zone", r.zone), ("source", r.source), ("rto", r.rto), ("remarks", r.remarks),
    ):
        if clean(raw_value) is None:
            defaulted_fields.append(field_key)
    if r.vehicle_age_from is None:
        defaulted_fields.append("vehicle_age_from")
    if r.vehicle_age_to is None:
        defaulted_fields.append("vehicle_age_to")

    return {
        "id": r.id,
        "upload_id": r.upload_id,
        "sheet_name": r.sheet_name,
        "lob": default_or(r.lob, "Motor"),
        "file_type": default_or(r.file_type, "ALL"),
        "insurance_company": r.insurance_company,
        "product": default_or(r.product, "ALL"),
        "product_label": master_data_service.expand_product(r.product, db),
        "policy_type": default_or(r.policy_type, "ALL"),
        "plan_type": default_or(
            r.plan_type,
            derive_plan_type(r.plan_type, r.policy_type, r.product, r.sub_class, r.remarks, r.raw_json),
        ),
        "sub_product": default_or(r.sub_product, "NA"),
        "class": default_or(r.class_, "NA"),
        "sub_class": default_or(r.sub_class, "ALL"),
        "make": default_or(r.make, "ALL"),
        "model": default_or(r.model, "ALL"),
        "fuel_type": default_or(r.fuel_type, "ALL"),
        "body_type": default_or(r.body_type, "ALL"),
        "vehicle_age_from": r.vehicle_age_from if r.vehicle_age_from is not None else 1,
        "vehicle_age_to": r.vehicle_age_to if r.vehicle_age_to is not None else 50,
        "cpa_status": default_or(r.cpa_status, "ALL"),
        "ncb_status": default_or(r.ncb_status, "ALL"),
        "partner_type": default_or(r.partner_type, "All Partners"),
        "state": default_or(r.state, "ALL"),
        "state_label": master_data_service.expand_state(r.state, db),
        "zone": default_or(r.zone, "ALL"),
        "source": default_or(r.source, "ALL"),
        "rto": default_or(r.rto, "ALL"),
        "effective_date": str(r.effective_date) if r.effective_date else None,
        "remarks": default_or(r.remarks, "ALL"),
        "commission_type": r.commission_type,
        "commissionType": r.commission_type,
        "slab_configuration": r.slab_configuration,
        "slabConfiguration": r.slab_configuration,
        "payin_od": payin_od,
        "payout_od": compute_payout(payin_od),
        "payin_tp": payin_tp,
        "payout_tp": compute_payout(payin_tp),
        "payin_net": payin_net,
        "payout_net": compute_payout(payin_net),
        "payin_reward": payin_reward,
        "payout_reward": compute_payout(payin_reward),
        "payin_scheme": payin_scheme,
        "payout_scheme": compute_payout(payin_scheme),
        "validation_status": r.validation_status,
        "warnings": r.warnings,
        "raw_json": r.raw_json,
        "slabs": [_serialize_slab(s) for s in r.slabs],
        "_defaulted_fields": defaulted_fields,
    }
