from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class LoanRecommendationRequest(BaseModel):
    customer_name: str = Field(..., min_length=1)

    age: int = Field(..., ge=18)

    employment_type: str = Field(..., min_length=1)

    work_experience_years: int = Field(..., ge=0)

    monthly_income: float = Field(..., gt=0)

    existing_emi: float = Field(..., ge=0)

    credit_score: int = Field(..., ge=300, le=900)

    loan_amount: float = Field(..., gt=0)

    loan_type: str = Field(..., min_length=1)

    property_value: float = Field(..., gt=0)

    property_type: str = Field(..., min_length=1)

    @field_validator(
        "customer_name",
        "employment_type",
        "loan_type",
        "property_type",
        mode="before",
    )
    @classmethod
    def strip_and_validate_text(cls, value):
        if value is None:
            return value

        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("This field is required.")

        return value


class RecommendedBank(BaseModel):
    bank_name: str
    loan_product: str
    interest_rate: float
    processing_fee: float
    max_tenure: int
    score: float
    required_documents: List[str]

    approval_probability: Optional[str] = None
    reason: Optional[str] = None
    advantages: Optional[List[str]] = None
    disadvantages: Optional[List[str]] = None

    monthly_emi: Optional[float] = None
    total_interest: Optional[float] = None
    total_payment: Optional[float] = None

class RejectedBank(BaseModel):
    bank_name: str
    reasons: List[str]


class LoanRecommendationResponse(BaseModel):
    recommendations: List[RecommendedBank]
    rejected_banks: List[RejectedBank] = []
