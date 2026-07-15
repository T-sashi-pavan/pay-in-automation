import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database.session import Base, get_db
from backend.app.models.upload_history import UploadHistory
from backend.app.models.commission_rule import CommissionRule
from backend.app.models.slab_detail import SlabDetail

# Setup in-memory SQLite DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_automation.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_automation_endpoints():
    db = TestingSessionLocal()
    # Clean up previous records if any
    db.query(SlabDetail).delete()
    db.query(CommissionRule).delete()
    db.query(UploadHistory).delete()
    db.commit()
    
    # 1. Create a dummy upload history
    upload = UploadHistory(
        filename="shriram_test.xlsx",
        company="Shriram",
        status="COMPLETED",
        total_records=2
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    
    # 2. Create one non-slab rule
    non_slab = CommissionRule(
        upload_id=upload.id,
        sheet_name="Sheet1",
        lob="Motor",
        file_type="New",
        insurance_company="Shriram",
        product="GCCV",
        policy_type="Comprehensive",
        state="MH",
        commission_type="NON_SLAB",
        validation_status="VALID",
        payin_od=0.15
    )
    db.add(non_slab)
    
    # 3. Create one slab rule
    slab = CommissionRule(
        upload_id=upload.id,
        sheet_name="Sheet1",
        lob="Motor",
        file_type="New",
        insurance_company="Shriram",
        product="GCCV",
        policy_type="Third Party",
        state="MH",
        commission_type="SLAB",
        validation_status="VALID",
        payin_tp=0.12
    )
    db.add(slab)
    db.commit()
    db.refresh(slab)
    
    # Add slab details
    sd = SlabDetail(
        commission_rule_id=slab.id,
        slab_from=0,
        slab_to=1000,
        payin_od=0.12,
        payin_tp=0.10,
        payin_type="PERCENTAGE"
    )
    db.add(sd)
    db.commit()
    
    # Test GET /api/automation/uploads
    res = client.get("/api/automation/uploads")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    target = next(u for u in data if u["id"] == upload.id)
    assert target["filename"] == "shriram_test.xlsx"
    assert target["slab_rows_count"] == 1
    assert target["non_slab_rows_count"] == 1
    assert target["total_rows"] == 2
    
    # Test GET /api/automation/uploads/{id}/valid-rows
    res_rows = client.get(f"/api/automation/uploads/{upload.id}/valid-rows")
    assert res_rows.status_code == 200
    rows_data = res_rows.json()
    assert rows_data["non_slab"] is not None
    assert rows_data["slab"] is not None
    assert rows_data["non_slab"]["payin_od"] == 15.0  # Serialized to percentage (0.15 * 100)
    assert rows_data["slab"]["payin_tp"] == 12.0
    
    # Test GET /api/automation/uploads/{id}/unique-values
    res_uniq = client.get(f"/api/automation/uploads/{upload.id}/unique-values")
    assert res_uniq.status_code == 200
    uniq_data = res_uniq.json()
    assert "GCCV" in uniq_data["product"]
    assert "MH" in uniq_data["state"]
    assert "Comprehensive" in uniq_data["policy_type"]
    
    # Clean up test database file
    db.close()
    import os
    if os.path.exists("./test_automation.db"):
        try:
            os.remove("./test_automation.db")
        except:
            pass
