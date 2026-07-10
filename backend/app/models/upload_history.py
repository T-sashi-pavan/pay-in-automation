from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class UploadHistory(Base):
    __tablename__ = "upload_history"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    company = Column(String(100), nullable=True)
    uploaded_by = Column(String(100), nullable=True, default="System")
    uploaded_at = Column(DateTime, nullable=False, server_default=func.now())
    status = Column(String(50), nullable=False, default="PROCESSING")  # PROCESSING, COMPLETED, FAILED
    total_records = Column(Integer, nullable=False, default=0)

    # Relationship to commission rules
    rules = relationship("CommissionRule", back_populates="upload", cascade="all, delete-orphan")
