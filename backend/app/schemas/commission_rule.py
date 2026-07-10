from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date
from backend.app.schemas.slab_detail import SlabDetail

class CommissionRuleBase(BaseModel):
    sheet_name: str
    lob: Optional[str] = None
    file_type: Optional[str] = None
    insurance_company: Optional[str] = None
    product: Optional[str] = None
    policy_type: Optional[str] = None
    plan_type: Optional[str] = None
    sub_product: Optional[str] = None
    class_: Optional[str] = Field(None, alias="class")
    sub_class: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    fuel_type: Optional[str] = None
    body_type: Optional[str] = None
    vehicle_age_from: Optional[int] = None
    vehicle_age_to: Optional[int] = None
    cpa_status: Optional[str] = None
    ncb_status: Optional[str] = None
    partner_type: Optional[str] = None
    state: Optional[str] = None
    zone: Optional[str] = None
    source: Optional[str] = None
    rto: Optional[str] = None
    effective_date: Optional[date] = None
    remarks: Optional[str] = None
    
    commission_type: Optional[str] = "NON_SLAB"
    slab_configuration: Optional[bool] = False
    
    payin_od: Optional[float] = None
    payout_od: Optional[float] = None
    payin_tp: Optional[float] = None
    payout_tp: Optional[float] = None
    payin_net: Optional[float] = None
    payout_net: Optional[float] = None
    payin_reward: Optional[float] = None
    payout_reward: Optional[float] = None
    payin_scheme: Optional[float] = None
    payout_scheme: Optional[float] = None
    
    raw_json: Optional[Dict[str, Any]] = None
    validation_status: str = "VALID"
    warnings: Optional[List[str]] = None

class CommissionRuleCreate(CommissionRuleBase):
    pass

class CommissionRule(CommissionRuleBase):
    id: int
    upload_id: int
    slabs: List[SlabDetail] = []

    class Config:
        from_attributes = True
        populate_by_name = True
