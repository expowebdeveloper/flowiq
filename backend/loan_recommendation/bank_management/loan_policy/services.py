from sqlalchemy.orm import Session

from loan_recommendation.bank_management.loan_policy.crud import (
    get_bank_policies,
    create_loan_policy,
    get_policy,
    update_policy,
    delete_policy
)

from loan_recommendation.bank_management.loan_policy.schemas import (
    LoanPolicyCreate
)

class LoanPolicyService:

    def get_bank_policies(
        self,
        db: Session,
        bank_id: int
    ):

        return get_bank_policies(
            db=db,
            bank_id=bank_id
        )
    
    def create_loan_policy(
        self,
        db: Session,
        bank_id: int,
        policy: LoanPolicyCreate
    ):

        return create_loan_policy(
            db=db,
            bank_id=bank_id,
            policy=policy
        )
    def get_policy(
        self,
        db: Session,
        policy_id: int
    ):

        return get_policy(
            db=db,
            policy_id=policy_id
        )
    

    def update_policy(
        self,
        db: Session,
        policy,
        data: LoanPolicyCreate
    ):

        return update_policy(
            db=db,
            policy=policy,
            data=data
        )
    
    def delete_policy(
        self,
        db: Session,
        policy
    ):

        return delete_policy(
            db=db,
            policy=policy
        )