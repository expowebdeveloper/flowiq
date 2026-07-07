from typing import Optional

from pydantic import BaseModel


class LoanCategoryRequest(BaseModel):
    type: str


class BankLoanRateEntry(BaseModel):
    bank_name: str
    loan_type: str
    interest_rate: str
    details: Optional[str] = None
    required_documents: Optional[str] = None
    source_url: Optional[str] = None


class BankLoanRatesBulkRequest(BaseModel):
    rates: list[BankLoanRateEntry]
