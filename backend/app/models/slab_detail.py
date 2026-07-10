from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class SlabDetail(Base):
    __tablename__ = "slab_details"

    id = Column(Integer, primary_key=True, index=True)
    commission_rule_id = Column(Integer, ForeignKey("commission_rules.id", ondelete="CASCADE"), nullable=False)
    
    payin_type = Column(String(50), nullable=True)  # PERCENTAGE, FLAT
    premium_type = Column(String(50), nullable=True)  # OD, TP, NET
    slab_from = Column(Float, nullable=True)
    slab_to = Column(Float, nullable=True)
    
    payin_od = Column(Float, nullable=True)
    payout_od = Column(Float, nullable=True)
    payin_tp = Column(Float, nullable=True)
    payout_tp = Column(Float, nullable=True)
    payin_net = Column(Float, nullable=True)
    payout_net = Column(Float, nullable=True)

    # Relationships
    rule = relationship("CommissionRule", back_populates="slabs")
