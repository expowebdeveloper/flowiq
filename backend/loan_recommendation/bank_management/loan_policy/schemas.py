from pydantic import BaseModel


class LoanPolicyCreate(BaseModel):

    # Only loan_type is required — toggling a loan type "on" for a bank
    # creates a bare policy row with everything else left null, to be filled
    # in later via the full policy-details form. Every other column is
    # nullable at the DB level (loan_recommendation/models.py), so this
    # matches what's actually storable.

    loan_type: str

    min_cibil: int | None = None

    max_cibil: int | None = None

    min_income: float | None = None

    max_loan_amount: float | None = None

    interest_rate: float | None = None

    processing_fee: float | None = None

    max_ltv: float | None = None

    min_age: int | None = None

    max_age: int | None = None

    minimum_work_experience_years: int | None = None

    maximum_foir: float | None = None

    employment_types: str | None = None

    property_types: str | None = None

    required_documents: str | None = None

    special_features: str | None = None

    prepayment_charges: str | None = None

    foreclosure_charges: str | None = None

    min_tenure: int | None = None

    max_tenure: int | None = None