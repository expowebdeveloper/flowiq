from fastapi import HTTPException
from sqlalchemy import func
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


def bank_exists_by_name(
    db: Session,
    name: str,
    exclude_id: int | None = None
):

    query = db.query(Bank).filter(Bank.name == name)
    if exclude_id is not None:
        query = query.filter(Bank.id != exclude_id)
    return query.first() is not None


def bank_exists_by_email(
    db: Session,
    email: str,
    exclude_id: int | None = None
):

    query = db.query(Bank).filter(func.lower(Bank.contact_email) == email.lower())
    if exclude_id is not None:
        query = query.filter(Bank.id != exclude_id)
    return query.first() is not None


def create_bank(
    db: Session,
    bank: BankCreate
):

    if bank_exists_by_name(db, bank.name):
        raise HTTPException(status_code=400, detail="A bank with this name already exists.")

    if bank.contact_email and bank_exists_by_email(db, bank.contact_email):
        raise HTTPException(status_code=400, detail="A bank with this contact email already exists.")

    new_bank = Bank(

        name=bank.name,

        website=bank.website,

        logo=bank.logo,

        status=bank.status,

        contact_email=bank.contact_email,

        portal_url=bank.portal_url,

        portal_username=bank.portal_username,

        portal_password=bank.portal_password

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

    if bank_exists_by_name(db, bank_data.name, exclude_id=bank.id):
        raise HTTPException(status_code=400, detail="A bank with this name already exists.")

    if bank_data.contact_email and bank_exists_by_email(db, bank_data.contact_email, exclude_id=bank.id):
        raise HTTPException(status_code=400, detail="A bank with this contact email already exists.")

    bank.name = bank_data.name

    bank.website = bank_data.website

    bank.logo = bank_data.logo

    bank.status = bank_data.status

    bank.contact_email = bank_data.contact_email

    bank.portal_url = bank_data.portal_url

    bank.portal_username = bank_data.portal_username

    bank.portal_password = bank_data.portal_password

    db.commit()

    db.refresh(bank)

    return bank

def delete_bank(
    db: Session,
    bank: Bank
):

    db.delete(bank)

    db.commit()
