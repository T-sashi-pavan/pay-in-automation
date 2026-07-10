from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class CommissionRule(Base):
    __tablename__ = "commission_rules"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("upload_history.id", ondelete="CASCADE"), nullable=False)
    sheet_name = Column(String(255), nullable=False)
    
    lob = Column(String(255), nullable=True)
    file_type = Column(String(255), nullable=True)
    insurance_company = Column(String(255), nullable=True)
    product = Column(String(500), nullable=True)
    policy_type = Column(String(255), nullable=True)
    plan_type = Column(String(255), nullable=True)
    sub_product = Column(String(255), nullable=True)
    class_ = Column("class", String(255), nullable=True)
    sub_class = Column(String(255), nullable=True)
    make = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    fuel_type = Column(String(255), nullable=True)
    body_type = Column(String(255), nullable=True)
    vehicle_age_from = Column(Integer, nullable=True)
    vehicle_age_to = Column(Integer, nullable=True)
    cpa_status = Column(String(255), nullable=True)
    ncb_status = Column(String(255), nullable=True)
    partner_type = Column(String(255), nullable=True)
    state = Column(String(500), nullable=True)
    zone = Column(String(255), nullable=True)
    source = Column(String(255), nullable=True)
    rto = Column(String(500), nullable=True)
    effective_date = Column(Date, nullable=True)
    remarks = Column(Text, nullable=True)
    
    commission_type = Column(String(50), nullable=True, default="NON_SLAB")
    slab_configuration = Column(Boolean, nullable=True, default=False)
    
    payin_od = Column(Float, nullable=True)
    payout_od = Column(Float, nullable=True)
    payin_tp = Column(Float, nullable=True)
    payout_tp = Column(Float, nullable=True)
    payin_net = Column(Float, nullable=True)
    payout_net = Column(Float, nullable=True)
    payin_reward = Column(Float, nullable=True)
    payout_reward = Column(Float, nullable=True)
    payin_scheme = Column(Float, nullable=True)
    payout_scheme = Column(Float, nullable=True)
    
    raw_json = Column(JSON, nullable=True)
    validation_status = Column(String(50), nullable=False, default="VALID")
    warnings = Column(JSON, nullable=True)

    # Relationships
    upload = relationship("UploadHistory", back_populates="rules")
    slabs = relationship("SlabDetail", back_populates="rule", cascade="all, delete-orphan")
