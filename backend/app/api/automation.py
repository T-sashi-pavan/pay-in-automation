from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Any, Optional

from backend.app.database.session import get_db
from backend.app.models.upload_history import UploadHistory
from backend.app.models.commission_rule import CommissionRule
from backend.app.services.rule_serializer import serialize_commission_rule

router = APIRouter(prefix="/api/automation")

@router.get("/uploads")
def get_uploads_for_automation(db: Session = Depends(get_db)):
    """
    Returns list of all uploads with separate Slab, Non-Slab, and total rule counts.
    """
    try:
        histories = db.query(UploadHistory).order_by(desc(UploadHistory.uploaded_at)).all()
        results = []
        for h in histories:
            slab_count = db.query(CommissionRule).filter(
                CommissionRule.upload_id == h.id,
                CommissionRule.commission_type == "SLAB"
            ).count()
            non_slab_count = db.query(CommissionRule).filter(
                CommissionRule.upload_id == h.id,
                CommissionRule.commission_type == "NON_SLAB"
            ).count()
            
            results.append({
                "id": h.id,
                "filename": h.filename,
                "company": h.company,
                "status": h.status,
                "uploaded_at": h.uploaded_at,
                "slab_rows_count": slab_count,
                "non_slab_rows_count": non_slab_count,
                "total_rows": h.total_records or (slab_count + non_slab_count)
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch uploads: {str(e)}")

@router.get("/uploads/{upload_id}/valid-rows")
def get_valid_rows_for_automation(upload_id: int, db: Session = Depends(get_db)):
    """
    Returns the first valid Non-Slab and Slab rule for the given upload history ID.
    """
    try:
        # Find first valid non-slab rule (having essential fields and validation status VALID)
        non_slab_rule = db.query(CommissionRule).filter(
            CommissionRule.upload_id == upload_id,
            CommissionRule.commission_type == "NON_SLAB",
            CommissionRule.validation_status == "VALID",
            CommissionRule.insurance_company.isnot(None),
            CommissionRule.product.isnot(None),
            CommissionRule.policy_type.isnot(None),
            CommissionRule.state.isnot(None)
        ).first()
        
        # Find first valid slab rule
        slab_rule = db.query(CommissionRule).filter(
            CommissionRule.upload_id == upload_id,
            CommissionRule.commission_type == "SLAB",
            CommissionRule.validation_status == "VALID",
            CommissionRule.insurance_company.isnot(None),
            CommissionRule.product.isnot(None),
            CommissionRule.policy_type.isnot(None),
            CommissionRule.state.isnot(None)
        ).first()
        
        return {
            "non_slab": serialize_commission_rule(non_slab_rule, db) if non_slab_rule else None,
            "slab": serialize_commission_rule(slab_rule, db) if slab_rule else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch valid rows: {str(e)}")

@router.get("/uploads/{upload_id}/unique-values")
def get_unique_values_for_upload(upload_id: int, db: Session = Depends(get_db)):
    """
    Returns lists of unique values present for the selected upload history.
    This dynamically populates dropdowns restricting choices strictly to that insurer's parsed rules.
    """
    try:
        rules = db.query(CommissionRule).filter(CommissionRule.upload_id == upload_id).all()
        fields = [
            "product", "sub_product", "plan_type", "policy_type", "fuel_type",
            "partner_type", "zone", "source", "rto", "state", "make", "model",
            "class_", "sub_class", "cpa_status", "ncb_status"
        ]
        unique_vals = {f: set() for f in fields}
        for r in rules:
            for f in fields:
                val = getattr(r, f)
                if val:
                    if f == "state":
                        # Split multi-states
                        for s in str(val).split(","):
                            s_clean = s.strip()
                            if s_clean:
                                unique_vals[f].add(s_clean)
                    else:
                        unique_vals[f].add(str(val).strip())
                        
        return {k: sorted(list(v)) for k, v in unique_vals.items()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch unique fields: {str(e)}")

@router.post("/run")
def run_automation_simulation(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Triggers Playwright to automate CRM entry on the mock CRM frontend.
    """
    upload_id = payload.get("upload_id")
    frontend_url = payload.get("frontend_url") or "http://localhost:5173"
    if not upload_id:
        raise HTTPException(status_code=400, detail="upload_id is required")
        
    try:
        # Fetch valid rules
        non_slab_rule = db.query(CommissionRule).filter(
            CommissionRule.upload_id == upload_id,
            CommissionRule.commission_type == "NON_SLAB",
            CommissionRule.validation_status == "VALID",
            CommissionRule.insurance_company.isnot(None),
            CommissionRule.product.isnot(None),
            CommissionRule.policy_type.isnot(None),
            CommissionRule.state.isnot(None)
        ).first()
        
        slab_rule = db.query(CommissionRule).filter(
            CommissionRule.upload_id == upload_id,
            CommissionRule.commission_type == "SLAB",
            CommissionRule.validation_status == "VALID",
            CommissionRule.insurance_company.isnot(None),
            CommissionRule.product.isnot(None),
            CommissionRule.policy_type.isnot(None),
            CommissionRule.state.isnot(None)
        ).first()
        
        if not non_slab_rule and not slab_rule:
            raise HTTPException(
                status_code=400,
                detail="No valid slab or non-slab rows found for automation in this upload"
            )
            
        non_slab_dict = serialize_commission_rule(non_slab_rule, db) if non_slab_rule else None
        slab_dict = serialize_commission_rule(slab_rule, db) if slab_rule else None
        
        from backend.app.services.automation_service import run_playwright_simulation
        res = run_playwright_simulation(frontend_url, non_slab_dict, slab_dict)
        
        if not res["success"]:
            raise HTTPException(status_code=500, detail=f"Playwright automation failed: {res['error']}")
            
        return res
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing simulation: {str(e)}")
