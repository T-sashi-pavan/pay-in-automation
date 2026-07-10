import os
import shutil
import uuid
import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_, and_, insert
from typing import List, Optional, Dict, Any

from backend.app.database.session import get_db
from backend.app.models.upload_history import UploadHistory
from backend.app.models.commission_rule import CommissionRule
from backend.app.models.slab_detail import SlabDetail
from backend.app.services.excel_parser.parser import ExcelParserService
from backend.app.services.rule_serializer import serialize_commission_rule

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

# Ensure uploads directory exists
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

excel_parser_service = ExcelParserService()

@router.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload .xlsx or .xls files.")

    # Create temporary file path
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save uploaded file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create processing record in UploadHistory
    upload_history = UploadHistory(
        filename=file.filename,
        company="Detecting...",
        status="PROCESSING",
        total_records=0
    )
    db.add(upload_history)
    db.commit()
    db.refresh(upload_history)

    # Read and parse file
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        parsed_rules = excel_parser_service.parse_workbook(file_bytes, filename=file.filename)

        if not parsed_rules:
            # Update status to failed if no rules could be parsed
            upload_history.status = "FAILED"
            upload_history.company = "N/A"
            db.commit()
            raise HTTPException(status_code=422, detail="No valid commission tables detected in the workbook.")

        # Detect primary insurer from parsed rules
        detected_company = "Unknown Insurer"
        for rule in parsed_rules:
            if rule.get("insurance_company"):
                detected_company = rule["insurance_company"]
                break
        
        upload_history.company = detected_company

        # Save rules and slabs in optimized chunks
        rules_to_insert = []
        for rule in parsed_rules:
            slabs_data = rule.pop("slabs", [])
            rule["upload_id"] = upload_history.id
            rules_to_insert.append((rule, slabs_data))

        batch_size = 1000
        for i in range(0, len(rules_to_insert), batch_size):
            batch = rules_to_insert[i:i+batch_size]
            
            # Map parameters and handle attribute "class_" to column "class" mapping
            rules_dicts = []
            for r_data, _ in batch:
                d = r_data.copy()
                if "class_" in d:
                    d["class"] = d.pop("class_")
                rules_dicts.append(d)
                
            # Core insert rules and retrieve generated primary key IDs
            result = db.execute(
                insert(CommissionRule).returning(CommissionRule.id),
                rules_dicts
            )
            inserted_ids = [row[0] for row in result.all()]
            
            # Prep slabs to insert mapped to retrieved rule IDs
            slabs_dicts = []
            for idx, (_, slabs) in enumerate(batch):
                rule_id = inserted_ids[idx]
                for s in slabs:
                    s["commission_rule_id"] = rule_id
                    slabs_dicts.append(s)
            
            if slabs_dicts:
                db.execute(
                    insert(SlabDetail),
                    slabs_dicts
                )

        upload_history.status = "COMPLETED"
        upload_history.total_records = len(parsed_rules)
        db.commit()

        # Clean up local file
        if os.path.exists(file_path):
            os.remove(file_path)

        return {
            "upload_id": upload_history.id,
            "filename": upload_history.filename,
            "total_records": upload_history.total_records
        }

    except HTTPException as he:
        # Cleanup file if present
        if os.path.exists(file_path):
            os.remove(file_path)
        raise he
    except Exception as e:
        logger.error(f"Error processing workbook parsing: {e}")
        upload_history.status = "FAILED"
        db.commit()
        # Cleanup file if present
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Database or parsing error: {str(e)}")


@router.get("/uploads")
def get_uploads(db: Session = Depends(get_db)):
    """
    Returns list of upload histories sorted by upload time.
    """
    try:
        histories = db.query(UploadHistory).order_by(desc(UploadHistory.uploaded_at)).all()
        return histories
    except Exception as e:
        logger.error(f"Failed to fetch uploads: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve upload history.")


@router.get("/uploads/{upload_id}")
def get_extracted_records(
    upload_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1),
    search: Optional[str] = Query(None),
    lob: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    product: Optional[str] = Query(None),
    policy_type: Optional[str] = Query(None),
    plan_type: Optional[str] = Query(None),
    sub_product: Optional[str] = Query(None),
    class_name: Optional[str] = Query(None, alias="class"),
    sub_class: Optional[str] = Query(None),
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    fuel_type: Optional[str] = Query(None),
    body_type: Optional[str] = Query(None),
    cpa_status: Optional[str] = Query(None),
    ncb_status: Optional[str] = Query(None),
    partner_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    rto: Optional[str] = Query(None),
    validation_status: Optional[str] = Query(None),
    commission_type: Optional[str] = Query(None),
    has_slabs: Optional[str] = Query(None),
    vehicle_age: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns the parsed commission rules and associated slabs for an upload, 
    with pagination, filter parameters, and search query.
    """
    upload = db.query(UploadHistory).filter(UploadHistory.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload record not found.")

    query = db.query(CommissionRule).options(joinedload(CommissionRule.slabs)).filter(CommissionRule.upload_id == upload_id)

    # Dynamic dynamic filters helper map (excluding list/special values state, rto, vehicle_age, has_slabs, commission_type)
    filter_map = {
        "lob": CommissionRule.lob,
        "file_type": CommissionRule.file_type,
        "insurance_company": CommissionRule.insurance_company,
        "product": CommissionRule.product,
        "policy_type": CommissionRule.policy_type,
        "plan_type": CommissionRule.plan_type,
        "sub_product": CommissionRule.sub_product,
        "class_": CommissionRule.class_,
        "sub_class": CommissionRule.sub_class,
        "make": CommissionRule.make,
        "model": CommissionRule.model,
        "fuel_type": CommissionRule.fuel_type,
        "body_type": CommissionRule.body_type,
        "cpa_status": CommissionRule.cpa_status,
        "ncb_status": CommissionRule.ncb_status,
        "partner_type": CommissionRule.partner_type,
        "zone": CommissionRule.zone,
        "source": CommissionRule.source,
        "validation_status": CommissionRule.validation_status,
    }

    for param_name, db_field in filter_map.items():
        val = None
        if param_name == "insurance_company":
            val = company
        elif param_name == "class_":
            val = class_name
        else:
            val = locals().get(param_name)
            
        if val:
            vals = [v.strip() for v in val.split(",") if v.strip()]
            if vals:
                if param_name in ("validation_status",):
                    query = query.filter(db_field.in_(vals))
                else:
                    query = query.filter(or_(*[db_field.ilike(f"%{v}%") for v in vals]))

    # Special/explode filters
    if state:
        state_vals = [v.strip() for v in state.split(",") if v.strip()]
        if state_vals:
            query = query.filter(or_(*[CommissionRule.state.ilike(f"%{v}%") for v in state_vals]))
            
    if rto:
        rto_vals = [v.strip() for v in rto.split(",") if v.strip()]
        if rto_vals:
            query = query.filter(or_(*[CommissionRule.rto.ilike(f"%{v}%") for v in rto_vals]))

    if commission_type:
        ct_vals = [v.strip().upper().replace("-", "_") for v in commission_type.split(",") if v.strip()]
        if ct_vals:
            query = query.filter(CommissionRule.commission_type.in_(ct_vals))

    if vehicle_age:
        age_vals = [v.strip() for v in vehicle_age.split(",") if v.strip()]
        if age_vals:
            age_clauses = []
            for age_str in age_vals:
                if "upto" in age_str.lower() or "5" in age_str:
                    age_clauses.append(and_(CommissionRule.vehicle_age_from == 0, CommissionRule.vehicle_age_to == 5))
                elif "6" in age_str or "15" in age_str:
                    age_clauses.append(and_(CommissionRule.vehicle_age_from == 6, CommissionRule.vehicle_age_to == 15))
                elif ">" in age_str or "above" in age_str or "15" in age_str:
                    age_clauses.append(CommissionRule.vehicle_age_from >= 16)
            if age_clauses:
                query = query.filter(or_(*age_clauses))

    if has_slabs:
        if has_slabs == "yes":
            query = query.join(CommissionRule.slabs).filter(
                SlabDetail.id.isnot(None)
            ).distinct()
        elif has_slabs == "no":
            valid_slabs_subquery = db.query(SlabDetail.commission_rule_id).filter(
                or_(
                    SlabDetail.payin_od.isnot(None),
                    SlabDetail.payin_tp.isnot(None),
                    SlabDetail.payin_net.isnot(None)
                )
            ).subquery()
            query = query.filter(~CommissionRule.id.in_(valid_slabs_subquery))

    # Apply general search term
    if search:
        search_filter = or_(
            CommissionRule.insurance_company.ilike(f"%{search}%"),
            CommissionRule.lob.ilike(f"%{search}%"),
            CommissionRule.product.ilike(f"%{search}%"),
            CommissionRule.policy_type.ilike(f"%{search}%"),
            CommissionRule.state.ilike(f"%{search}%"),
            CommissionRule.remarks.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    # Perform counts for pagination metadata
    total_items = query.count()
    
    # Retrieve items
    offset = (page - 1) * limit
    rules = query.offset(offset).limit(limit).all()

    # Build response records with nested slabs details
    records = [serialize_commission_rule(r, db) for r in rules]

    return {
        "metadata": {
            "total": total_items,
            "page": page,
            "limit": limit,
            "pages": (total_items + limit - 1) // limit if total_items > 0 else 0,
            "filename": upload.filename,
            "company": upload.company
        },
        "records": records
    }


@router.delete("/uploads/{upload_id}")
def delete_upload(upload_id: int, db: Session = Depends(get_db)):
    """
    Deletes the upload history record and all its related commission rules and slabs.
    """
    upload = db.query(UploadHistory).filter(UploadHistory.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload record not found.")

    try:
        # 1. Bulk delete child SlabDetail records to prevent cascade loading timeouts
        db.query(SlabDetail).filter(
            SlabDetail.commission_rule_id.in_(
                db.query(CommissionRule.id).filter(CommissionRule.upload_id == upload_id)
            )
        ).delete(synchronize_session=False)

        # 2. Bulk delete CommissionRule records
        db.query(CommissionRule).filter(CommissionRule.upload_id == upload_id).delete(synchronize_session=False)

        # 3. Delete UploadHistory record
        db.delete(upload)
        db.commit()
        return {"message": "Upload history and all its parsed rules deleted successfully."}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete upload history: {e}")
        raise HTTPException(status_code=500, detail="Database error during deletion.")
@router.get("/filters")
def get_distinct_filters(upload_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """
    Returns distinct values with per-value row counts for every key filter field across ALL uploads (or filtered by upload_id).
    Each field returns a list of {"value": str, "count": int} objects, sorted by count descending.
    """
    try:
        from sqlalchemy import func

        # Define field mapping: response_key -> model_attribute
        field_map = {
            "insurance_company": CommissionRule.insurance_company,
            "lob":               CommissionRule.lob,
            "file_type":         CommissionRule.file_type,
            "product":           CommissionRule.product,
            "policy_type":       CommissionRule.policy_type,
            "plan_type":         CommissionRule.plan_type,
            "sub_product":       CommissionRule.sub_product,
            "class_":            CommissionRule.class_,
            "sub_class":         CommissionRule.sub_class,
            "make":              CommissionRule.make,
            "model":             CommissionRule.model,
            "fuel_type":         CommissionRule.fuel_type,
            "body_type":         CommissionRule.body_type,
            "cpa_status":        CommissionRule.cpa_status,
            "ncb_status":        CommissionRule.ncb_status,
            "partner_type":      CommissionRule.partner_type,
            "zone":              CommissionRule.zone,
            "source":            CommissionRule.source,
            "remarks":           CommissionRule.remarks,
            "commission_type":   CommissionRule.commission_type,
            "validation_status": CommissionRule.validation_status,
        }

        results = {}
        # Effective Date options
        date_query = db.query(CommissionRule.effective_date, func.count(CommissionRule.id).label("cnt"))\
            .filter(CommissionRule.effective_date.isnot(None))
        if upload_id is not None:
            date_query = date_query.filter(CommissionRule.upload_id == upload_id)
        date_rows = date_query.group_by(CommissionRule.effective_date).order_by(func.count(CommissionRule.id).desc()).all()
        results["effective_date"] = [
            {"value": str(val), "count": int(cnt)}
            for val, cnt in date_rows
            if val
        ]
        for key, attr in field_map.items():
            query = db.query(attr, func.count(CommissionRule.id).label("cnt"))\
                .filter(attr.isnot(None))\
                .filter(func.trim(attr) != "")
            if upload_id is not None:
                query = query.filter(CommissionRule.upload_id == upload_id)
            rows = query.group_by(attr).order_by(func.count(CommissionRule.id).desc()).all()
            results[key] = [
                {"value": str(val).strip(), "count": int(cnt)}
                for val, cnt in rows
                if str(val).strip()
            ]

        # State — values may be comma-separated; explode and count individually
        state_query = db.query(CommissionRule.state)\
            .filter(CommissionRule.state.isnot(None))\
            .filter(func.trim(CommissionRule.state) != "")
        if upload_id is not None:
            state_query = state_query.filter(CommissionRule.upload_id == upload_id)
        state_rows = state_query.all()
        state_counts: dict = {}
        for (state_val,) in state_rows:
            if state_val:
                for part in str(state_val).split(","):
                    part = part.strip()
                    if part and part.lower() not in ("rto only", ""):
                        state_counts[part] = state_counts.get(part, 0) + 1
        results["state"] = sorted(
            [{"value": v, "count": c} for v, c in state_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )

        # RTO — may also be comma-separated
        rto_query = db.query(CommissionRule.rto)\
            .filter(CommissionRule.rto.isnot(None))\
            .filter(func.trim(CommissionRule.rto) != "")
        if upload_id is not None:
            rto_query = rto_query.filter(CommissionRule.upload_id == upload_id)
        rto_rows = rto_query.all()
        rto_counts: dict = {}
        for (rto_val,) in rto_rows:
            if rto_val:
                for part in str(rto_val).split(","):
                    part = part.strip()
                    if part:
                        rto_counts[part] = rto_counts.get(part, 0) + 1
        results["rto"] = sorted(
            [{"value": v, "count": c} for v, c in rto_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )

        logger.info(f"[FILTERS] Options counts: { {k: len(v) for k, v in results.items()} }")
        return results
    except Exception as e:
        logger.error(f"Failed to fetch distinct filters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load dynamic filters.")


@router.post("/search")
def search_all_rules(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Queries across ALL uploaded Excel records using dynamic multi-select filters and search.
    Returns all records when no filters are applied.
    """
    try:
        filters_payload = payload.get("filters", {})
        search = payload.get("search")
        page = int(payload.get("page", 1))
        limit = int(payload.get("limit", 50))
        
        query = (
            db.query(CommissionRule)
            .options(joinedload(CommissionRule.slabs))
            .join(UploadHistory)
        )
        
        # Map frontend filter keys to model attributes
        filter_key_map = {
            "insurer":      "insurance_company",
            "insuranceCompany": "insurance_company",
            "class":        "class_",
            "lob":          "lob",
            "fileType":     "file_type",
            "file_type":    "file_type",
            "product":      "product",
            "policyType":   "policy_type",
            "policy_type":  "policy_type",
            "planType":     "plan_type",
            "plan_type":    "plan_type",
            "subProduct":   "sub_product",
            "sub_product":  "sub_product",
            "subClass":     "sub_class",
            "sub_class":    "sub_class",
            "make":         "make",
            "model":        "model",
            "fuelType":     "fuel_type",
            "fuel_type":    "fuel_type",
            "bodyType":     "body_type",
            "body_type":    "body_type",
            "cpaStatus":    "cpa_status",
            "cpa_status":   "cpa_status",
            "ncbStatus":    "ncb_status",
            "ncb_status":   "ncb_status",
            "partnerType":  "partner_type",
            "partner_type": "partner_type",
            "zone":         "zone",
            "source":       "source",
            "rto":          "rto",
            "remarks":      "remarks",
            "validationStatus": "validation_status",
            "validation_status": "validation_status",
            "commissionType": "commission_type",
            "commission_type": "commission_type",
        }

        for fe_key, values in filters_payload.items():
            if fe_key in ("vehicle_age", "state", "effective_date", "effectiveDate") or not values:
                continue
            if fe_key in ("commission_type", "commissionType"):
                cleaned_ct_vals = []
                for v in values:
                    cleaned_ct_vals.append(str(v).strip().upper().replace("-", "_"))
                if cleaned_ct_vals:
                    query = query.filter(CommissionRule.commission_type.in_(cleaned_ct_vals))
                continue
            model_field = filter_key_map.get(fe_key, fe_key)
            if hasattr(CommissionRule, model_field):
                attr = getattr(CommissionRule, model_field)
                or_clauses = [attr.ilike(f"%{v}%") for v in values]
                query = query.filter(or_(*or_clauses))

        # State filter — stored values may be multi-state comma strings
        state_values = filters_payload.get("state", [])
        if state_values:
            state_clauses = [CommissionRule.state.ilike(f"%{v}%") for v in state_values]
            query = query.filter(or_(*state_clauses))

        # Vehicle age filter
        vehicle_ages = filters_payload.get("vehicle_age", [])
        if vehicle_ages:
            age_clauses = []
            for age_str in vehicle_ages:
                lower = age_str.lower()
                if "upto" in lower or ("5" in age_str and "15" not in age_str and "6" not in age_str):
                    age_clauses.append(and_(CommissionRule.vehicle_age_from <= 5, CommissionRule.vehicle_age_to <= 5))
                elif "6" in age_str or "15" in age_str:
                    age_clauses.append(and_(CommissionRule.vehicle_age_from >= 6, CommissionRule.vehicle_age_to <= 15))
                elif ">" in age_str or "above" in lower:
                    age_clauses.append(CommissionRule.vehicle_age_from >= 16)
            if age_clauses:
                query = query.filter(or_(*age_clauses))
                
        # Effective Date multi-select filter
        effective_dates = filters_payload.get("effective_date", []) or filters_payload.get("effectiveDate", [])
        if effective_dates:
            from datetime import datetime
            parsed_dates = []
            for dt_str in effective_dates:
                try:
                    parsed_dates.append(datetime.strptime(str(dt_str).split(" ")[0].strip(), "%Y-%m-%d").date())
                except:
                    pass
            if parsed_dates:
                query = query.filter(CommissionRule.effective_date.in_(parsed_dates))
                
        # Date range filter
        date_from = payload.get("effective_date_from")
        date_to = payload.get("effective_date_to")
        if date_from:
            query = query.filter(CommissionRule.effective_date >= date_from)
        if date_to:
            query = query.filter(CommissionRule.effective_date <= date_to)
            
        # Global text search
        if search:
            search_filter = or_(
                CommissionRule.insurance_company.ilike(f"%{search}%"),
                CommissionRule.lob.ilike(f"%{search}%"),
                CommissionRule.product.ilike(f"%{search}%"),
                CommissionRule.policy_type.ilike(f"%{search}%"),
                CommissionRule.state.ilike(f"%{search}%"),
                CommissionRule.remarks.ilike(f"%{search}%"),
                UploadHistory.filename.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
            
        query = query.order_by(desc(UploadHistory.uploaded_at), desc(CommissionRule.id))
        
        total_items = query.count()
        offset = (page - 1) * limit
        rules = query.offset(offset).limit(limit).all()
        
        records = []
        for r in rules:
            rule_dict = serialize_commission_rule(r, db)
            rule_dict["upload_filename"] = r.upload.filename
            rule_dict["upload_date"] = str(r.upload.uploaded_at) if r.upload.uploaded_at else None
            records.append(rule_dict)
            
        logger.info(f"[SEARCH] Returned {len(records)}/{total_items} records for page {page}")
        return {
            "metadata": {
                "total": total_items,
                "page": page,
                "limit": limit,
                "pages": (total_items + limit - 1) // limit if total_items > 0 else 0
            },
            "records": records
        }
    except Exception as e:
        logger.error(f"Global search query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error during search: {str(e)}")
