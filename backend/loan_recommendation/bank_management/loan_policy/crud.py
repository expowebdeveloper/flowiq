from sqlalchemy.orm import Session
from loan_recommendation.models import BankLoanPolicy
from loan_recommendation.bank_management.loan_policy.schemas import LoanPolicyCreate


def get_bank_policies(
    db: Session,
    bank_id: int
):

    return (
        db.query(BankLoanPolicy)
        .filter(
            BankLoanPolicy.bank_id == bank_id
        )
        .order_by(
            BankLoanPolicy.loan_type
        )
        .all()
    )


def create_loan_policy(
    db: Session,
    bank_id: int,
    policy: LoanPolicyCreate
):

    new_policy = BankLoanPolicy(

        bank_id=bank_id,

        loan_type=policy.loan_type,

        min_cibil=policy.min_cibil,

        max_cibil=policy.max_cibil,

        min_income=policy.min_income,

        max_loan_amount=policy.max_loan_amount,

        interest_rate=policy.interest_rate,

        processing_fee=policy.processing_fee,

        max_ltv=policy.max_ltv,

        min_age=policy.min_age,

        max_age=policy.max_age,

        minimum_work_experience_years=policy.minimum_work_experience_years,

        maximum_foir=policy.maximum_foir,

        employment_types=policy.employment_types,

        property_types=policy.property_types,

        required_documents=policy.required_documents,

        special_features=policy.special_features,

        prepayment_charges=policy.prepayment_charges,

        foreclosure_charges=policy.foreclosure_charges,

        min_tenure=policy.min_tenure,

        max_tenure=policy.max_tenure

    )

    db.add(new_policy)

    db.commit()

    db.refresh(new_policy)

    return new_policy

def get_policy(
    db: Session,
    policy_id: int
):

    return (
        db.query(BankLoanPolicy)
        .filter(
            BankLoanPolicy.id == policy_id
        )
        .first()
    )


def update_policy(
    db: Session,
    policy: BankLoanPolicy,
    data: LoanPolicyCreate
):

    policy.loan_type = data.loan_type

    policy.min_cibil = data.min_cibil

    policy.max_cibil = data.max_cibil

    policy.min_income = data.min_income

    policy.max_loan_amount = data.max_loan_amount

    policy.interest_rate = data.interest_rate

    policy.processing_fee = data.processing_fee

    policy.max_ltv = data.max_ltv

    policy.min_age = data.min_age

    policy.max_age = data.max_age

    policy.minimum_work_experience_years = (
        data.minimum_work_experience_years
    )

    policy.maximum_foir = data.maximum_foir

    policy.employment_types = data.employment_types

    policy.property_types = data.property_types

    policy.required_documents = data.required_documents

    policy.special_features = data.special_features

    policy.prepayment_charges = data.prepayment_charges

    policy.foreclosure_charges = data.foreclosure_charges

    policy.min_tenure = data.min_tenure

    policy.max_tenure = data.max_tenure

    db.commit()

    db.refresh(policy)

    return policy

def delete_policy(
    db: Session,
    policy: BankLoanPolicy
):

    db.delete(policy)

    db.commit()