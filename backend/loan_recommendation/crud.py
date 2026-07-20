import json
from sqlalchemy.orm import Session
from loan_recommendation.models import (
    LoanRecommendation,
    Bank,
    BankLoanPolicy
)


def get_saved_recommendation(
    db: Session,
    request
):

    return (
        db.query(LoanRecommendation)
        .filter(
            LoanRecommendation.customer_name == request.customer_name,
            LoanRecommendation.loan_amount == request.loan_amount,
            LoanRecommendation.loan_type == request.loan_type,
            LoanRecommendation.credit_score == request.credit_score
        )
        .first()
    )


def save_recommendation(
    db: Session,
    request,
    response
):

    recommendation = LoanRecommendation(

        customer_name=request.customer_name,
        age=request.age,
        employment_type=request.employment_type,
        work_experience_years=request.work_experience_years,
        monthly_income=request.monthly_income,
        existing_emi=request.existing_emi,
        credit_score=request.credit_score,
        loan_amount=request.loan_amount,
        loan_type=request.loan_type,
        property_value=request.property_value,
        property_type=request.property_type,

        response=json.dumps(response)

    )

    db.add(recommendation)

    db.commit()

    db.refresh(recommendation)

    return recommendation


def get_bank_by_name(
    db: Session,
    name: str
):
    return (
        db.query(Bank)
        .filter(Bank.name == name)
        .first()
    )


def create_bank(
    db: Session,
    name: str,
    website: str = None,
    logo: str = None
):
    bank = Bank(
        name=name,
        website=website,
        logo=logo
    )

    db.add(bank)
    db.commit()
    db.refresh(bank)

    return bank

def create_bank_policy(
    db: Session,
    bank_id: int,
    loan_type: str,
    min_cibil: int,
    max_cibil: int,
    min_income: float,
    max_loan_amount: float,
    interest_rate: float,
    processing_fee: float,
    max_ltv: float,
    min_age: int,
    max_age: int,
    minimum_work_experience_years: int,
    maximum_foir: float,
    employment_types: str,
    property_types: str,
    required_documents: str,
    special_features: str,
    prepayment_charges: str,
    foreclosure_charges: str,
    min_tenure: int,
    max_tenure: int
):

    policy = BankLoanPolicy(

        bank_id=bank_id,

        loan_type=loan_type,

        min_cibil=min_cibil,

        max_cibil=max_cibil,

        min_income=min_income,

        max_loan_amount=max_loan_amount,

        interest_rate=interest_rate,

        processing_fee=processing_fee,

        max_ltv=max_ltv,

        min_age=min_age,

        max_age=max_age,

        minimum_work_experience_years=minimum_work_experience_years,

        maximum_foir=maximum_foir,

        employment_types=employment_types,

        property_types=property_types,

        required_documents=required_documents,

        special_features=special_features,

        prepayment_charges=prepayment_charges,

        foreclosure_charges=foreclosure_charges,

        min_tenure=min_tenure,

        max_tenure=max_tenure

    )

    db.add(policy)

    db.commit()

    db.refresh(policy)

    return policy

def get_eligible_banks(
    db: Session,
    loan_type: str,
    cibil: int,
    income: float,
    loan_amount: float
):

    print("=" * 80)
    print("Loan Type :", repr(loan_type))
    print("CIBIL     :", cibil)
    print("Income    :", income)
    print("Loan Amount:", loan_amount)
    print("=" * 80)

    results = (
        db.query(BankLoanPolicy, Bank)
        .join(Bank)
        .filter(
            BankLoanPolicy.loan_type == loan_type,
            BankLoanPolicy.min_cibil <= cibil,
            BankLoanPolicy.max_cibil >= cibil,
            BankLoanPolicy.min_income <= income,
            BankLoanPolicy.max_loan_amount >= loan_amount
        )
        .all()
    )

    print("Rows returned from SQL:", len(results))

    eligible_banks = []

    for policy, bank in results:


        print("=" * 50)
        print("Bank:", bank.name)
        print("employment_types:", repr(policy.employment_types))
        print("property_types:", repr(policy.property_types))
        print("required_documents:", repr(policy.required_documents))
        print("special_features:", repr(policy.special_features))

        eligible_banks.append({
            "bank_name": bank.name,
            "loan_product": policy.loan_type,
            "interest_rate": policy.interest_rate,
            "processing_fee": policy.processing_fee,
            "max_tenure": policy.max_tenure,
            "min_credit_score": policy.min_cibil,
            "min_monthly_income": policy.min_income,
            "max_loan_amount": policy.max_loan_amount,
            "max_ltv": policy.max_ltv,
            "min_age": policy.min_age,
            "max_age": policy.max_age,
            "employment_types": json.loads(policy.employment_types),
            "minimum_work_experience_years": policy.minimum_work_experience_years,
            "maximum_foir": policy.maximum_foir,
            "property_types": json.loads(policy.property_types),
            "required_documents": json.loads(policy.required_documents),
            "special_features": json.loads(policy.special_features),
            "prepayment_charges": policy.prepayment_charges,
            "foreclosure_charges": policy.foreclosure_charges,
        })

    return eligible_banks

def get_bank_policy(
    db: Session,
    bank_id: int,
    loan_type: str
):
    return (
        db.query(BankLoanPolicy)
        .filter(
            BankLoanPolicy.bank_id == bank_id,
            BankLoanPolicy.loan_type == loan_type
        )
        .first()
    )

def update_bank_policy(
    db: Session,
    policy: BankLoanPolicy,
    bank_data: dict
):

    policy.min_cibil = bank_data["min_credit_score"]

    policy.max_cibil = 900

    policy.min_income = bank_data["min_monthly_income"]

    policy.max_loan_amount = bank_data["max_loan_amount"]

    policy.interest_rate = bank_data["interest_rate"]

    policy.processing_fee = bank_data["processing_fee"]

    policy.max_ltv = bank_data["max_ltv"]

    policy.min_age = bank_data["min_age"]

    policy.max_age = bank_data["max_age"]

    policy.minimum_work_experience_years = bank_data["minimum_work_experience_years"]

    policy.maximum_foir = bank_data["maximum_foir"]

    policy.employment_types = json.dumps(
        bank_data["employment_types"]
    )

    policy.property_types = json.dumps(
        bank_data["property_types"]
    )

    policy.required_documents = json.dumps(
        bank_data["required_documents"]
    )

    policy.special_features = json.dumps(
        bank_data["special_features"]
    )

    policy.prepayment_charges = bank_data["prepayment_charges"]

    policy.foreclosure_charges = bank_data["foreclosure_charges"]

    policy.max_tenure = bank_data["max_tenure"]

    db.commit()

    db.refresh(policy)

    return policy