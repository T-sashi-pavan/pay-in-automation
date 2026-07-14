"""
Covers rule_serializer.py's `_defaulted_fields` signal — the flag that tells
the frontend/export layer "this cell's value is a business default, not
something actually extracted from the source file", so it can be shown in
orange instead of looking identical to real data.

Uses lightweight stub objects instead of real SQLAlchemy models — expand_state
and expand_product both short-circuit on a falsy raw value without touching
the db session, so a plain `None` stands in for it here.
"""
from types import SimpleNamespace

from backend.app.services.rule_serializer import serialize_commission_rule, _serialize_slab


def _make_rule(**overrides):
    defaults = dict(
        id=1, upload_id=1, sheet_name="Sheet1",
        lob=None, file_type=None, insurance_company="Shriram", product=None,
        policy_type="Comprehensive", plan_type=None, sub_product=None, class_=None,
        sub_class="GVW 3501-7500", make=None, model=None, fuel_type=None, body_type=None,
        vehicle_age_from=None, vehicle_age_to=10, cpa_status=None, ncb_status="YES",
        partner_type=None, state=None, zone=None, source=None, rto=None,
        effective_date=None, remarks=None,
        commission_type="NON_SLAB", slab_configuration=False,
        payin_od=80.0, payout_od=None, payin_tp=None, payout_tp=None,
        payin_net=None, payout_net=None, payin_reward=None, payout_reward=None,
        payin_scheme=None, payout_scheme=None,
        validation_status="VALID", warnings=[], raw_json={}, slabs=[],
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_null_fields_are_flagged_defaulted_populated_fields_are_not():
    rule = _make_rule()
    data = serialize_commission_rule(rule, db=None)

    defaulted = set(data["_defaulted_fields"])

    # Genuinely null on the stub -> must be flagged
    for field in ("lob", "file_type", "product", "plan_type", "sub_product", "class",
                  "make", "model", "fuel_type", "body_type", "cpa_status",
                  "partner_type", "state", "zone", "source", "rto", "remarks", "vehicle_age_from"):
        assert field in defaulted, f"{field} was null on the stub and should be flagged as defaulted"

    # Genuinely populated on the stub -> must NOT be flagged
    for field in ("policy_type", "sub_class", "ncb_status", "vehicle_age_to"):
        assert field not in defaulted, f"{field} had a real value and should not be flagged as defaulted"

    # insurance_company has no default_or fallback at all — never tracked
    assert "insurance_company" not in defaulted


def test_serialize_slab_flags_null_boundary_and_type_fields():
    slab = SimpleNamespace(
        id=1, payin_type=None, premium_type=None, slab_from=None, slab_to=100000,
        payin_od=30.0, payin_tp=None, payin_net=None,
    )
    data = _serialize_slab(slab)
    defaulted = set(data["_defaulted_fields"])

    assert "payin_type" in defaulted
    assert "premium_type" in defaulted
    assert "slab_from" in defaulted
    assert "slab_to" not in defaulted  # was genuinely populated (100000)


def test_serialize_slab_with_everything_populated_flags_nothing():
    slab = SimpleNamespace(
        id=1, payin_type="PERCENTAGE", premium_type="OD", slab_from=0, slab_to=40,
        payin_od=30.0, payin_tp=None, payin_net=None,
    )
    data = _serialize_slab(slab)
    assert data["_defaulted_fields"] == []
