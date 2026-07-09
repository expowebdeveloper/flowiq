import sys
import os

# ── Path Bootstrap ─────────────────────────────────────────────────────────────
# Add the backend/ directory to sys.path so that every module inside it
# (db, config, company, dashboard, loan_recommendation, …) can be imported
# using plain names (e.g. `from db import Base`) instead of `backend.db`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── FastAPI Imports ────────────────────────────────────────────────────────────
from fastapi import FastAPI, APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# ── Internal Imports ───────────────────────────────────────────────────────────
from db import Base, engine
from company.models import Company
from loan_recommendation.models import LoanRecommendation

from dashboard.routes import router as dashboard_router
from company.routes import router as company_router
from company.company_lookup.routes import router as company_lookup_router
from loan_recommendation.routes import router as loan_router
from loan_recommendation.recommendation import router as recommendation_router
from loan_recommendation.bank_sync.routes import router as bank_sync_router
from loan_recommendation.bank_sync.scheduler import start_scheduler
from loan_recommendation.bank_management.routes import router as bank_management_router
from loan_recommendation.bank_management.loan_policy.routes import router as loan_policy_router

# ── Database Init ──────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="FlowIQ", version="1.0.0")

# Start background bank scheduler
start_scheduler()

# ── Static Files ───────────────────────────────────────────────────────────────
# static/ lives at the project root (sibling of backend/), so we point two
# levels up from this file to resolve correctly regardless of cwd.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(_ROOT, "static")), name="static")

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(dashboard_router,       tags=["Dashboard"])
app.include_router(company_router,         prefix="/companies", tags=["Companies"])
app.include_router(company_lookup_router)
app.include_router(loan_router,            tags=["Loan Recommendation"])
app.include_router(recommendation_router)
app.include_router(bank_sync_router)
app.include_router(bank_management_router)
app.include_router(loan_policy_router)