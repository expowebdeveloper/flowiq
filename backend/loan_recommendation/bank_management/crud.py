from sqlalchemy.orm import Session
from loan_recommendation.models import Bank
from loan_recommendation.bank_management.schemas import BankCreate


def get_all_banks(
    db: Session
):

    return (
        db.query(Bank)
        .order_by(Bank.name)
        .all()
    )

def create_bank(
    db: Session,
    bank: BankCreate
):

    new_bank = Bank(

        name=bank.name,

        website=bank.website,

        logo=bank.logo,

        status=bank.status

    )

    db.add(new_bank)

    db.commit()

    db.refresh(new_bank)

    return new_bank

def get_bank(
    db: Session,
    bank_id: int
):

    return (
        db.query(Bank)
        .filter(
            Bank.id == bank_id
        )
        .first()
    )


def update_bank(
    db: Session,
    bank: Bank,
    bank_data: BankCreate
):

    bank.name = bank_data.name

    bank.website = bank_data.website

    bank.logo = bank_data.logo

    bank.status = bank_data.status

    db.commit()

    db.refresh(bank)

    return bank

def delete_bank(
    db: Session,
    bank: Bank
):

    db.delete(bank)

    db.commit()