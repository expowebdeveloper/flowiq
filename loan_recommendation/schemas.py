from typing import List, Optional
from pydantic import BaseModel


class LoanRecommendationRequest(BaseModel):
    customer_name: str

    age: int

    employment_type: str

    work_experience_years: int

    monthly_income: float

    existing_emi: float

    credit_score: int

    loan_amount: float

    loan_type: str

    property_value: float

    property_type: str


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


class LoanRecommendationResponse(BaseModel):
    recommendations: List[RecommendedBank]