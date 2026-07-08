from fastapi import APIRouter, Depends, HTTPException

from auth import require_broker
from db import LoanCategory, get_session

from .constants import LOAN_TYPES
from .schemas import LoanCategoryRequest

router = APIRouter(prefix="/broker/loan-categories", tags=["loan-categories"])


@router.get("")
def list_loan_categories(current_user: dict = Depends(require_broker)):
    session = get_session()
    try:
        rows = session.query(LoanCategory).filter(
            LoanCategory.broker_id == current_user["sub"], LoanCategory.is_active == True
        ).all()
        return {
            "available_types": LOAN_TYPES,
            "categories": [{"id": r.id, "type": r.type} for r in rows],
        }
    finally:
        session.close()


@router.post("")
def add_loan_category(req: LoanCategoryRequest, current_user: dict = Depends(require_broker)):
    if req.type not in LOAN_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of {LOAN_TYPES}")

    session = get_session()
    try:
        existing = session.query(LoanCategory).filter(
            LoanCategory.broker_id == current_user["sub"], LoanCategory.type == req.type
        ).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                session.commit()
            return {"id": existing.id, "type": existing.type}

        category = LoanCategory(broker_id=current_user["sub"], type=req.type)
        session.add(category)
        session.commit()
        session.refresh(category)
        return {"id": category.id, "type": category.type}
    finally:
        session.close()


@router.delete("/{category_id}")
def remove_loan_category(category_id: str, current_user: dict = Depends(require_broker)):
    session = get_session()
    try:
        row = session.query(LoanCategory).filter(
            LoanCategory.id == category_id, LoanCategory.broker_id == current_user["sub"]
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="Category not found")
        row.is_active = False
        session.commit()
        return {"status": "removed"}
    finally:
        session.close()
