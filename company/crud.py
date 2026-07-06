from sqlalchemy.orm import Session

from company.models import Company
from company.schemas import CompanyCreate, CompanyUpdate


def create_company(db: Session, company: CompanyCreate, logo: str | None = None):
    db_company = Company(**company.model_dump(), logo=logo)

    db.add(db_company)
    db.commit()
    db.refresh(db_company)

    return db_company

def get_all_companies(db: Session):
    return db.query(Company).all()

def get_company_by_id(db: Session, company_id: int):
    return (
        db.query(Company).filter(Company.id == company_id).first()
    )

def update_company(
    db: Session,
    db_company: Company,
    company: CompanyUpdate,
    logo: str | None = None
):
    update_data = company.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_company, key, value)

    if logo is not None:
        db_company.logo = logo

    db.commit()
    db.refresh(db_company)

    return db_company

def delete_company(db:Session, db_company: Company):
    db.delete(db_company)
    db.commit()

    