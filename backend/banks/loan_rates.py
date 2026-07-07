from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import require_broker
from db import BankLoanRate, get_session

from .constants import LOAN_TYPES
from .schemas import BankLoanRateEntry, BankLoanRatesBulkRequest

router = APIRouter(prefix="/bank-loan-rates", tags=["loan-rates"])


@router.post("/bank")
def add_bank_loan_rate(req: BankLoanRateEntry, current_user: dict = Depends(require_broker)):
    """Add a single bank loan rate entry (bank_name + loan_type is unique)."""
    if req.loan_type not in LOAN_TYPES:
        raise HTTPException(status_code=400, detail=f"loan_type must be one of {LOAN_TYPES}")

    session = get_session()
    try:
        existing = session.query(BankLoanRate).filter(
            BankLoanRate.bank_name == req.bank_name, BankLoanRate.loan_type == req.loan_type
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Bank '{req.bank_name}' already has a rate for loan_type '{req.loan_type}'",
            )

        bank = BankLoanRate(
            bank_name=req.bank_name,
            loan_type=req.loan_type,
            interest_rate=req.interest_rate,
            details=req.details,
            required_documents=req.required_documents,
            source_url=req.source_url,
        )
        session.add(bank)
        session.commit()
        session.refresh(bank)
        return {
            "id": bank.id, "bank_name": bank.bank_name, "loan_type": bank.loan_type,
            "interest_rate": bank.interest_rate, "details": bank.details,
            "required_documents": bank.required_documents, "source_url": bank.source_url,
        }
    finally:
        session.close()


@router.post("")
def save_bank_loan_rates(req: BankLoanRatesBulkRequest, current_user: dict = Depends(require_broker)):
    """Bulk upsert bank loan rate data (bank_name + loan_type is unique)."""
    invalid = [r.loan_type for r in req.rates if r.loan_type not in LOAN_TYPES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid loan_type(s): {invalid}. Must be one of {LOAN_TYPES}")

    session = get_session()
    try:
        saved = []
        for r in req.rates:
            existing = session.query(BankLoanRate).filter(
                BankLoanRate.bank_name == r.bank_name, BankLoanRate.loan_type == r.loan_type
            ).first()
            if existing:
                existing.interest_rate = r.interest_rate
                existing.details = r.details
                existing.required_documents = r.required_documents
                existing.source_url = r.source_url
            else:
                existing = BankLoanRate(
                    bank_name=r.bank_name,
                    loan_type=r.loan_type,
                    interest_rate=r.interest_rate,
                    details=r.details,
                    required_documents=r.required_documents,
                    source_url=r.source_url,
                )
                session.add(existing)
            saved.append(existing)
        session.commit()
        for r in saved:
            session.refresh(r)
        return {
            "status": "saved",
            "count": len(saved),
            "rates": [
                {
                    "id": r.id, "bank_name": r.bank_name, "loan_type": r.loan_type,
                    "interest_rate": r.interest_rate, "details": r.details,
                    "required_documents": r.required_documents, "source_url": r.source_url,
                }
                for r in saved
            ],
        }
    finally:
        session.close()


@router.get("")
def list_bank_loan_rates(
    bank_name: Optional[str] = Query(None),
    loan_type: Optional[str] = Query(None),
):
    """Public read of stored bank loan rate data, optionally filtered."""
    session = get_session()
    try:
        q = session.query(BankLoanRate)
        if bank_name:
            q = q.filter(BankLoanRate.bank_name == bank_name)
        if loan_type:
            q = q.filter(BankLoanRate.loan_type == loan_type)
        rows = q.order_by(BankLoanRate.bank_name, BankLoanRate.loan_type).all()
        return {
            "count": len(rows),
            "rates": [
                {
                    "id": r.id, "bank_name": r.bank_name, "loan_type": r.loan_type,
                    "interest_rate": r.interest_rate, "details": r.details,
                    "required_documents": r.required_documents, "source_url": r.source_url,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ],
        }
    finally:
        session.close()
