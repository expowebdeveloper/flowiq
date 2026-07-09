import os
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from company.models import Company
from loan_recommendation.models import Bank, LoanRecommendation
from db import get_db

router = APIRouter()

_HERE = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(_HERE, "templates"))


@router.get("/")
def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    company_count = db.query(Company).count()
    bank_count = db.query(Bank).count()
    loan_count = db.query(LoanRecommendation).count()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "company_count": company_count,
            "bank_count": bank_count,
            "broker_count": 0,
            "loan_count": loan_count
        }
    )


@router.get("/api-tester")
def api_tester(
    request: Request,
    db: Session = Depends(get_db)
):
    companies = db.query(Company).all()
    banks = db.query(Bank).all()
    
    return templates.TemplateResponse(
        request=request,
        name="api_tester.html",
        context={
            "companies": companies,
            "banks": banks
        }
    )