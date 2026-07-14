import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.uploads import router as uploads_router
from backend.app.api.rule_edit import router as rule_edit_router
from backend.app.api.master_data import router as master_data_router

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

@app.on_event("startup")
def on_startup():
    from backend.app.database.session import engine
    from sqlalchemy import text
    with engine.connect() as conn:
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
                pass

@app.get("/")
def read_root():
    return {"message": "Pay-In Automation Dashboard API is running."}
