from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db import get_db
from loan_recommendation.bank_management.loan_policy.services import LoanPolicyService
from loan_recommendation.bank_management.loan_policy.schemas import LoanPolicyCreate

router = APIRouter(
    prefix="/banks",
    tags=["Loan Policy"]
)

loan_policy_service = LoanPolicyService()


@router.get("/{bank_id}/policies")
def loan_policy_list(
    bank_id: int,
    db: Session = Depends(get_db)
):
    policies = loan_policy_service.get_bank_policies(db=db, bank_id=bank_id)
    return {
        "success": True,
        "bank_id": bank_id,
        "policies": policies
    }


@router.post("/{bank_id}/policies/add")
def create_policy(
    bank_id: int,
    policy: LoanPolicyCreate,
    db: Session = Depends(get_db)
):
    new_policy = loan_policy_service.create_loan_policy(db=db, bank_id=bank_id, policy=policy)
    return {
        "success": True,
        "message": "Loan policy created successfully.",
        "policy_id": new_policy.id if new_policy else None
    }


@router.post("/policies/{policy_id}/edit")
def update_policy(
    policy_id: int,
    data: LoanPolicyCreate,
    db: Session = Depends(get_db)
):
    policy = loan_policy_service.get_policy(db=db, policy_id=policy_id)
    if not policy:
        return {"success": False, "message": "Policy not found."}

    loan_policy_service.update_policy(db=db, policy=policy, data=data)
    return {
        "success": True,
        "message": "Loan policy updated successfully."
    }


@router.get("/policies/{policy_id}/delete")
@router.post("/policies/{policy_id}/delete")
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db)
):
    policy = loan_policy_service.get_policy(db=db, policy_id=policy_id)
    if policy is None:
        return {"success": False, "message": "Policy not found."}
    loan_policy_service.delete_policy(db=db, policy=policy)
    return {
        "success": True,
        "message": "Loan policy deleted successfully."
    }