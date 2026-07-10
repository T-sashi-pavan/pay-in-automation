from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UploadHistoryBase(BaseModel):
    filename: str
    company: Optional[str] = None
    uploaded_by: Optional[str] = "System"
    status: str = "PROCESSING"
    total_records: int = 0

class UploadHistoryCreate(UploadHistoryBase):
    pass

class UploadHistory(UploadHistoryBase):
    id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True
