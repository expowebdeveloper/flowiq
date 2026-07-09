import sys
import os

# ── Path Bootstrap ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ── Internal Imports ───────────────────────────────────────────────────────────
from db import Base, engine
from company.models import Company
from loan_recommendation.models import LoanRecommendation

# Existing Routers (ACO)
from auth import oauth_router
from inbound import router as inbound_router
from outbound import router as outbound_router
from agents import router as agents_router
from banks import loan_categories_router, loan_rates_router, loan_applications_router

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
app = FastAPI(title="Email AI & FlowIQ API", version="1.0.0")

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
app.include_router(inbound_router)
app.include_router(outbound_router)
app.include_router(agents_router)
app.include_router(loan_categories_router)
app.include_router(loan_rates_router)
app.include_router(loan_applications_router)

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
