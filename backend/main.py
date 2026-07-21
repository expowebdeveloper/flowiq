import sys
import os
import logging

# ── Path Bootstrap ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logging.handlers import RotatingFileHandler

_LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(_LOGS_DIR, exist_ok=True)

_log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_log_formatter)

_loan_apply_file_handler = RotatingFileHandler(
    os.path.join(_LOGS_DIR, "loan_apply.log"), maxBytes=5 * 1024 * 1024, backupCount=3
)
_loan_apply_file_handler.setFormatter(_log_formatter)

logging.basicConfig(level=logging.INFO, handlers=[_console_handler])

# loan_apply's logger additionally writes to its own log file, so the full
# submit -> agent -> send flow can be read start-to-end without console
# scrollback getting mixed in with every other router's log lines.
logging.getLogger("loan_apply").addHandler(_loan_apply_file_handler)

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ── Internal Imports ───────────────────────────────────────────────────────────
from db import Base, engine
from company.models import Company
from loan_recommendation.models import LoanRecommendation

# Existing Routers (ACO)
from auth import oauth_router, login_router
from inbound import router as inbound_router
from outbound import router as outbound_router
from agents import router as agents_router
from banks import (
    loan_categories_router,
    loan_rates_router,
    loan_applications_router,
    bank_notifications_router,
)
from chat import router as chat_router
from kyc import kyc_router
from loan_apply import router as loan_apply_router
from agent_activity.routes import router as agent_activity_router
import importlib.util
_json_routes_spec = importlib.util.spec_from_file_location(
    "json_verify_routes",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "json/routes.py")
)
_json_routes_module = importlib.util.module_from_spec(_json_routes_spec)
_json_routes_spec.loader.exec_module(_json_routes_module)
json_verify_router = _json_routes_module.router


# New Routers (Loan Recommendation)
from dashboard.routes import router as dashboard_router
from company.routes import router as company_router
from company.company_lookup.routes import router as company_lookup_router
from loan_recommendation.routes import router as loan_router
from loan_recommendation.recommendation import router as recommendation_router
from loan_recommendation.bank_sync.routes import router as bank_sync_router
from loan_recommendation.bank_sync.scheduler import start_scheduler
from loan_recommendation.bank_management.routes import router as bank_management_router
from loan_recommendation.bank_management.loan_policy.routes import router as loan_policy_router

load_dotenv()

# ── Database Init ──────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App ────────────────────────────────────────────────────────────────────────
# root_path tells FastAPI it's served externally under this prefix (e.g.
# "/api" behind the nginx proxy, which strips the prefix before forwarding)
# so /docs, /openapi.json, and redirect responses generate correct URLs.
# Routes below are still declared without the prefix — only link generation
# changes. https://fastapi.tiangolo.com/advanced/behind-a-proxy/
app = FastAPI(title="Email AI & FlowIQ API", version="1.0.0", root_path=os.getenv("ROOT_PATH", ""))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start background bank scheduler
start_scheduler()

# ── Static Files ───────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(_ROOT, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ── Routers ────────────────────────────────────────────────────────────────────
# Existing Routers
app.include_router(oauth_router)
app.include_router(login_router)
app.include_router(inbound_router)
app.include_router(outbound_router)
app.include_router(agents_router)
app.include_router(loan_categories_router)
app.include_router(loan_rates_router)
app.include_router(loan_applications_router)
app.include_router(bank_notifications_router)
app.include_router(chat_router)
app.include_router(kyc_router)
app.include_router(json_verify_router)
app.include_router(loan_apply_router)
app.include_router(agent_activity_router)

# Loan Recommendation / FlowIQ Routers
app.include_router(dashboard_router,       tags=["Dashboard"])
app.include_router(company_router,         prefix="/companies", tags=["Companies"])
app.include_router(company_lookup_router)
app.include_router(loan_router,            tags=["Loan Recommendation"])
app.include_router(recommendation_router)
app.include_router(bank_sync_router)
app.include_router(bank_management_router)
app.include_router(loan_policy_router)


@app.get("/", tags=["utility"])
def root():
    return {
        "service": "Email AI & FlowIQ API Gateway",
        "endpoints": {
            "1. Link email (OAuth)": "GET /auth/link?email=you@gmail.com",
            "2. Check auth status": "GET /auth/status?email=you@gmail.com",
            "3. List inbox (fast)": "GET /inbox?email=you@gmail.com&max_results=20",
            "4. Get single email + attachments": "GET /inbox/message/{id}?email=you@gmail.com",
            "5. Full inbox with bodies": "GET /inbox/full?email=you@gmail.com&max_results=10",
            "6. Download attachment": "GET /attachments/{email}/{filename}",
            "7. Loan Recommendation": "POST /loan-recommendation/recommend",
            "docs": "/docs",
        }
    }
