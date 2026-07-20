from typing import Optional

from pydantic import BaseModel, Field


class BankDecisionOut(BaseModel):
    bank_name: str
    status: str  # "rejected" | "offer" | "offer_more_documents"
    remarks: Optional[str] = None
    decided_at: str


class LoanApplyCreate(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    phone_number: str = Field(min_length=1)
    date_of_birth: str = Field(min_length=1)
    ssn: str = Field(min_length=1)
    gender: str = Field(min_length=1)
    citizenship_status: str = Field(min_length=1)
    current_address: str = Field(min_length=1)
    marital_status: str = Field(min_length=1)
    loan_type: str = Field(min_length=1)
    fico_score: int = Field(ge=300, le=850)
    zip_code: str = Field(min_length=1)
    loan_amount: float = Field(gt=0)
    extra_loan_details: Optional[dict] = None


class LoanApplyOut(LoanApplyCreate):
    id: str
    created_at: str
    documents_status: str = "awaiting_documents"
    extracted_data: Optional[dict] = None
    documents_processed_at: Optional[str] = None
    bank_decisions: list[BankDecisionOut] = []

    # Overrides LoanApplyCreate.loan_amount's gt=0 constraint, which is a
    # write-side validation rule (a new submission must specify a positive
    # amount) — not valid for read-side output, since submissions made
    # before this field existed have loan_amount=NULL in the database.
    loan_amount: float = Field(ge=0)

    # Overrides LoanApplyCreate.phone_number's required min_length=1 —
    # submissions made before this field existed have phone_number=NULL.
    phone_number: Optional[str] = None

    # Same as phone_number above — submissions made before these fields
    # existed have date_of_birth/ssn=NULL.
    date_of_birth: Optional[str] = None
    ssn: Optional[str] = None

    # Same as phone_number above — submissions made before these fields
    # existed have current_address/marital_status=NULL.
    current_address: Optional[str] = None
    marital_status: Optional[str] = None
