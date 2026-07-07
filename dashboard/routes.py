from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from db import get_db
from company.models import Company

router = APIRouter()

templates = Jinja2Templates(directory="dashboard/templates")


@router.get("/")
def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    company_count = db.query(Company).count()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "company_count": company_count,
            "bank_count": 0,
            "broker_count": 0,
            "loan_count": 0
        }
    )