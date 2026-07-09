from sqlalchemy.orm import Session
from loan_recommendation.bank_management.crud import (
    get_all_banks,
    create_bank,
    get_bank,
    update_bank,
    delete_bank
)
from loan_recommendation.bank_management.schemas import BankCreate

class BankManagementService:

    def get_all_banks(
        self,
        db: Session
    ):
        return get_all_banks(db)
    
    def create_bank(
        self,
        db: Session,
        bank: BankCreate
    ):
        return create_bank(
            db=db,
            bank=bank
        )
    
    def get_bank(
        self,
        db: Session,
        bank_id: int
    ):
        return get_bank(
            db=db,
            bank_id=bank_id
        )


    def update_bank(
        self,
        db: Session,
        bank,
        bank_data: BankCreate
    ):
        return update_bank(
            db=db,
            bank=bank,
            bank_data=bank_data
        )
    
    def delete_bank(
        self,
        db: Session,
        bank
    ):

        return delete_bank(
            db=db,
            bank=bank
        )