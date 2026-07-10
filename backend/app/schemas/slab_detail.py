from pydantic import BaseModel
from typing import Optional

class SlabDetailBase(BaseModel):
    payin_type: Optional[str] = None
    premium_type: Optional[str] = None
    slab_from: Optional[float] = None
    slab_to: Optional[float] = None
    payin_od: Optional[float] = None
    payout_od: Optional[float] = None
    payin_tp: Optional[float] = None
    payout_tp: Optional[float] = None
    payin_net: Optional[float] = None
    payout_net: Optional[float] = None

class SlabDetailCreate(SlabDetailBase):
    pass

class SlabDetail(SlabDetailBase):
    id: int
    commission_rule_id: int

    class Config:
        from_attributes = True
