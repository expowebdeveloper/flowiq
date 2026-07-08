from pydantic import BaseModel


class LoanPolicyCreate(BaseModel):

    loan_type: str

    min_cibil: int

    max_cibil: int

    min_income: float

    max_loan_amount: float

    interest_rate: float

    processing_fee: float

    max_ltv: float

    min_age: int

    max_age: int

    minimum_work_experience_years: int

    maximum_foir: float

    employment_types: str

    property_types: str

    required_documents: str

    special_features: str

    prepayment_charges: str

    foreclosure_charges: str

    min_tenure: int

    max_tenure: int