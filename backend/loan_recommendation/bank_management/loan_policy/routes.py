import os

from fastapi import APIRouter, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from db import get_db
from loan_recommendation.bank_management.loan_policy.services import LoanPolicyService
from loan_recommendation.bank_management.loan_policy.schemas import LoanPolicyCreate

router = APIRouter(
    prefix="/banks",
    tags=["Loan Policy"]
)

_HERE = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=[
    os.path.join(_HERE, "templates"),
    os.path.join(_HERE, "..", "..", "..", "dashboard", "templates"),
])
loan_policy_service = LoanPolicyService()


@router.get("/{bank_id}/policies")
def loan_policy_list(
    bank_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    policies = loan_policy_service.get_bank_policies(db=db, bank_id=bank_id)
    return templates.TemplateResponse(
        request=request,
        name="list.html",
        context={"bank_id": bank_id, "policies": policies}
    )


@router.get("/{bank_id}/policies/add")
def add_policy_page(bank_id: int, request: Request):
    return templates.TemplateResponse(
        request=request,
        name="add.html",
        context={"bank_id": bank_id}
    )


@router.post("/{bank_id}/policies/add")
def create_policy(
    bank_id: int,
    loan_type: str = Form(...),
    min_cibil: int = Form(...),
    max_cibil: int = Form(...),
    min_income: float = Form(...),
    max_loan_amount: float = Form(...),
    interest_rate: float = Form(...),
    processing_fee: float = Form(...),
    max_ltv: float = Form(...),
    min_age: int = Form(...),
    max_age: int = Form(...),
    minimum_work_experience_years: int = Form(...),
    maximum_foir: float = Form(...),
    employment_types: str = Form(...),
    property_types: str = Form(...),
    required_documents: str = Form(...),
    special_features: str = Form(""),
    prepayment_charges: str = Form(...),
    foreclosure_charges: str = Form(...),
    min_tenure: int = Form(...),
    max_tenure: int = Form(...),
    db: Session = Depends(get_db)
):
    policy = LoanPolicyCreate(
        loan_type=loan_type,
        min_cibil=min_cibil,
        max_cibil=max_cibil,
        min_income=min_income,
        max_loan_amount=max_loan_amount,
        interest_rate=interest_rate,
        processing_fee=processing_fee,
        max_ltv=max_ltv,
        min_age=min_age,
        max_age=max_age,
        minimum_work_experience_years=minimum_work_experience_years,
        maximum_foir=maximum_foir,
        employment_types=employment_types,
        property_types=property_types,
        required_documents=required_documents,
        special_features=special_features,
        prepayment_charges=prepayment_charges,
        foreclosure_charges=foreclosure_charges,
        min_tenure=min_tenure,
        max_tenure=max_tenure
    )
    loan_policy_service.create_loan_policy(db=db, bank_id=bank_id, policy=policy)
    return RedirectResponse(url=f"/banks/{bank_id}/policies", status_code=303)


@router.get("/policies/{policy_id}/edit")
def edit_policy_page(policy_id: int, request: Request, db: Session = Depends(get_db)):
    policy = loan_policy_service.get_policy(db=db, policy_id=policy_id)
    return templates.TemplateResponse(
        request=request,
        name="edit.html",
        context={"policy": policy}
    )


@router.post("/policies/{policy_id}/edit")
def update_policy(
    policy_id: int,
    loan_type: str = Form(...),
    min_cibil: int = Form(...),
    max_cibil: int = Form(...),
    min_income: float = Form(...),
    max_loan_amount: float = Form(...),
    interest_rate: float = Form(...),
    processing_fee: float = Form(...),
    max_ltv: float = Form(...),
    min_age: int = Form(...),
    max_age: int = Form(...),
    minimum_work_experience_years: int = Form(...),
    maximum_foir: float = Form(...),
    employment_types: str = Form(...),
    property_types: str = Form(...),
    required_documents: str = Form(...),
    special_features: str = Form(""),
    prepayment_charges: str = Form(...),
    foreclosure_charges: str = Form(...),
    min_tenure: int = Form(...),
    max_tenure: int = Form(...),
    db: Session = Depends(get_db)
):
    policy = loan_policy_service.get_policy(db=db, policy_id=policy_id)
    data = LoanPolicyCreate(
        loan_type=loan_type,
        min_cibil=min_cibil,
        max_cibil=max_cibil,
        min_income=min_income,
        max_loan_amount=max_loan_amount,
        interest_rate=interest_rate,
        processing_fee=processing_fee,
        max_ltv=max_ltv,
        min_age=min_age,
        max_age=max_age,
        minimum_work_experience_years=minimum_work_experience_years,
        maximum_foir=maximum_foir,
        employment_types=employment_types,
        property_types=property_types,
        required_documents=required_documents,
        special_features=special_features,
        prepayment_charges=prepayment_charges,
        foreclosure_charges=foreclosure_charges,
        min_tenure=min_tenure,
        max_tenure=max_tenure
    )
    loan_policy_service.update_policy(db=db, policy=policy, data=data)
    return RedirectResponse(url=f"/banks/{policy.bank_id}/policies", status_code=303)


@router.get("/policies/{policy_id}/delete")
def delete_policy(policy_id: int, db: Session = Depends(get_db)):
    policy = loan_policy_service.get_policy(db=db, policy_id=policy_id)
    if policy is None:
        return RedirectResponse(url="/banks/", status_code=303)
    bank_id = policy.bank_id
    loan_policy_service.delete_policy(db=db, policy=policy)
    return RedirectResponse(url=f"/banks/{bank_id}/policies", status_code=303)