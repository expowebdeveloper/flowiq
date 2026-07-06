import os
import uuid
import shutil

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from company import crud
from company.models import Company
from company.schemas import CompanyCreate, CompanyUpdate

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "uploads",
    "logos"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def save_logo(file: UploadFile | None):

    if file is None or not file.filename:
        return None

    allowed_extensions = {"jpg", "jpeg", "png", "webp"}

    extension = file.filename.rsplit(".", 1)[-1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Invalid logo format."
        )

    filename = f"{uuid.uuid4()}.{extension}"

    file_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return filename

def company_exists(db: Session, company_name: str):

    return (
        db.query(Company)
        .filter(Company.company_name == company_name)
        .first()
    )

def create_company_service(
    db: Session,
    company: CompanyCreate,
    logo: UploadFile | None = None
):

    if company_exists(db, company.company_name):
        raise HTTPException(
            status_code=400,
            detail="Company already exists."
        )

    logo_filename = save_logo(logo)

    return crud.create_company(
        db=db,
        company=company,
        logo=logo_filename
    )

def get_all_companies_service(db: Session):

    return crud.get_all_companies(db)

def get_company_service(
    db: Session,
    company_id: int
):

    company = crud.get_company_by_id(db, company_id)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found."
        )

    return company

def update_company_service(
    db: Session,
    company_id: int,
    company: CompanyUpdate,
    logo: UploadFile | None = None
):

    db_company = crud.get_company_by_id(
        db,
        company_id
    )

    if db_company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found."
        )

    logo_filename = None

    if logo and logo.filename:
        logo_filename = save_logo(logo)

    return crud.update_company(
        db=db,
        db_company=db_company,
        company=company,
        logo=logo_filename
    )


def delete_company_service(
    db: Session,
    company_id: int
):

    company = crud.get_company_by_id(db, company_id)

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found."
        )

    crud.delete_company(db, company)

