from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from company.models import Company
from loan_recommendation.models import Bank, LoanRecommendation
from db import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def dashboard(
    db: Session = Depends(get_db)
):
    company_count = db.query(Company).count()
    bank_count = db.query(Bank).count()
    loan_count = db.query(LoanRecommendation).count()

    return {
        "company_count": company_count,
        "bank_count": bank_count,
        "broker_count": 0,
        "loan_count": loan_count
    }