import json

from sqlalchemy.orm import Session
from sqlalchemy import func
from company.company_lookup.models import CompanyLookup
from company.company_lookup.schemas import CompanyLookupCreate


def get_company_by_name(
    db: Session,
    company_name: str
):

    company_name = company_name.strip().lower()

    return (
        db.query(CompanyLookup)
        .filter(
            func.lower(CompanyLookup.company_name) == company_name
        )
        .first()
    )

def create_company(
    db: Session,
    company: CompanyLookupCreate
):

    db_company = CompanyLookup(

        company_name=company.company_name,

        website=company.website,

        description=company.description,

        industry=company.industry,

        emails=json.dumps(company.emails),

        phones=json.dumps(company.phones),

        logo=company.logo,

        linkedin=company.linkedin,

        facebook=company.facebook,

        twitter=company.twitter,

        instagram=company.instagram,

        contact_page=company.contact_page,

        about_page=company.about_page

    )

    db.add(db_company)

    db.commit()

    db.refresh(db_company)

    return db_company