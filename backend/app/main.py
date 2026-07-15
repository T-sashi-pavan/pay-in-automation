import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.uploads import router as uploads_router
from backend.app.api.rule_edit import router as rule_edit_router
from backend.app.api.master_data import router as master_data_router
from backend.app.api.automation import router as automation_router

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

app = FastAPI(
    title="Pay-In Automation Dashboard API",
    version="1.0.0"
)

# CORS middleware setup — local dev origins always allowed; production frontend
# URL(s) come from the CORS_ORIGINS env var (comma-separated), since the
# deployed frontend's URL isn't known until it's actually created on Render.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
extra_origins = os.getenv("CORS_ORIGINS", "")
if extra_origins:
    origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(uploads_router)
app.include_router(rule_edit_router)
app.include_router(master_data_router)
app.include_router(automation_router)

@app.on_event("startup")
def on_startup():
    from backend.app.database.session import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        # 1. Ensure slab_details has conditional columns
        columns_to_add = [
            ("condition_field", "VARCHAR(255)"),
            ("operator", "VARCHAR(50)"),
            ("value", "FLOAT"),
            ("original_text", "TEXT")
        ]
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE slab_details ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                logger.info(f"Added column {col_name} to slab_details successfully.")
            except Exception:
                # Column already exists or other error — rollback so the connection
                # stays usable (critical for PostgreSQL which aborts on any error)
                conn.rollback()

        # 2. Upsert ALL Indian states so every deployment has them (safe to re-run)
        ALL_STATES = {
            "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam",
            "BR": "Bihar", "CG": "Chhattisgarh", "CT": "Chhattisgarh",
            "GA": "Goa", "GJ": "Gujarat", "HR": "Haryana",
            "HP": "Himachal Pradesh", "JH": "Jharkhand", "JK": "Jammu and Kashmir",
            "KA": "Karnataka", "KL": "Kerala", "LA": "Ladakh",
            "LD": "Lakshadweep", "MP": "Madhya Pradesh", "MH": "Maharashtra",
            "MN": "Manipur", "ML": "Meghalaya", "MZ": "Mizoram",
            "NL": "Nagaland", "OD": "Odisha", "OR": "Odisha",
            "PB": "Punjab", "RJ": "Rajasthan", "SK": "Sikkim",
            "TN": "Tamil Nadu", "TG": "Telangana", "TS": "Telangana",
            "TR": "Tripura", "UP": "Uttar Pradesh",
            "UK": "Uttarakhand", "UA": "Uttarakhand", "UT": "Uttarakhand",
            "WB": "West Bengal",
            "AN": "Andaman and Nicobar Islands", "CH": "Chandigarh",
            "DN": "Dadra and Nagar Haveli", "DD": "Daman and Diu",
            "DL": "Delhi", "PY": "Puducherry",
            "ALL": "All India",
            "ROM1": "ROM1", "ROM2": "ROM2", "ROM3": "ROM3", "ROM": "ROM",
            "HYDERABAD": "Hyderabad", "CHENNAI": "Chennai", "BANGALORE": "Bangalore",
            "CORPORATE REGION": "Corporate Region", "BRANCH REGION": "Branch Region",
            "REGIONAL OFFICE": "Regional Office",
        }
        try:
            # Create table if missing (fresh installs before alembic)
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS master_states "
                "(code VARCHAR(10) PRIMARY KEY, name VARCHAR(100) NOT NULL)"
            ))
            conn.commit()
            db_dialect = engine.dialect.name
            for code, name in ALL_STATES.items():
                try:
                    if db_dialect == "postgresql":
                        conn.execute(text(
                            "INSERT INTO master_states (code, name) VALUES (:c, :n) "
                            "ON CONFLICT (code) DO NOTHING"
                        ), {"c": code, "n": name})
                    else:
                        conn.execute(text(
                            "INSERT OR IGNORE INTO master_states (code, name) VALUES (:c, :n)"
                        ), {"c": code, "n": name})
                except Exception:
                    conn.rollback()
            conn.commit()
            logger.info("master_states upsert completed (%d states).", len(ALL_STATES))
        except Exception as e:
            logger.warning("Could not upsert master_states: %s", e)
            conn.rollback()

        # 3. Clear in-memory master-data cache so re-uploads pick up fresh state names
        try:
            from backend.app.services.master_data_service import clear_cache
            clear_cache()
        except Exception:
            pass


@app.get("/")
def read_root():
    return {"message": "Pay-In Automation Dashboard API is running."}
