from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from loan_recommendation.bank_management.schemas import BankCreate
from db import get_db
from loan_recommendation.bank_management.services import (
    BankManagementService
)

router = APIRouter(
    prefix="/banks",
    tags=["Bank Management"]
)

bank_service = BankManagementService()


@router.get("")
@router.get("/")
def bank_list(
    db: Session = Depends(get_db)
):
    banks = bank_service.get_all_banks(db)
    return {
        "success": True,
        "banks": banks
    }


@router.post("/add")
def create_bank(
    bank: BankCreate,
    db: Session = Depends(get_db)
):
    new_bank = bank_service.create_bank(
        db=db,
        bank=bank
    )
    return {
        "success": True,
        "message": "Bank added successfully.",
        "bank_id": new_bank.id if new_bank else None
    }


@router.post("/{bank_id}/edit")
def update_bank(
    bank_id: int,
    bank_data: BankCreate,
    db: Session = Depends(get_db)
):
    bank = bank_service.get_bank(
        db=db,
        bank_id=bank_id
    )
    if not bank:
        return {"success": False, "message": "Bank not found."}

    bank_service.update_bank(
        db=db,
        bank=bank,
        bank_data=bank_data
    )
    return {
        "success": True,
        "message": "Bank updated successfully."
    }


@router.get("/{bank_id}/delete")
@router.post("/{bank_id}/delete")
def delete_bank(
    bank_id: int,
    db: Session = Depends(get_db)
):
    bank = bank_service.get_bank(
        db=db,
        bank_id=bank_id
    )
    if bank:
        bank_service.delete_bank(
            db=db,
            bank=bank
        )
        return {
            "success": True,
            "message": "Bank deleted successfully."
        }
    return {
        "success": False,
        "message": "Bank not found."
    }
