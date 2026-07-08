from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi import Form
from fastapi.responses import RedirectResponse
from loan_recommendation.bank_management.schemas import BankCreate
from db import get_db
from loan_recommendation.bank_management.services import (
    BankManagementService
)

router = APIRouter(
    prefix="/banks",
    tags=["Bank Management"]
)

templates = Jinja2Templates(
    directory="loan_recommendation/bank_management/templates"
)

bank_service = BankManagementService()


@router.get("/")
def bank_list(
    request: Request,
    db: Session = Depends(get_db)
):

    banks = bank_service.get_all_banks(db)

    return templates.TemplateResponse(
        request=request,
        name="list.html",
        context={
            "banks": banks
        }
    )

@router.post("/add")
def create_bank(

    name: str = Form(...),

    website: str = Form(None),

    logo: str = Form(None),

    status: str = Form("active"),

    db: Session = Depends(get_db)

):

    bank = BankCreate(

        name=name,

        website=website,

        logo=logo,

        status=status

    )

    bank_service.create_bank(
        db=db,
        bank=bank
    )

    return RedirectResponse(
        url="/banks/",
        status_code=303
    )

@router.get("/add")
def add_bank_page(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="add.html",
        context={}
    )


@router.get("/{bank_id}/edit")
def edit_bank_page(
    bank_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    bank = bank_service.get_bank(
        db=db,
        bank_id=bank_id
    )

    return templates.TemplateResponse(
        request=request,
        name="edit.html",
        context={
            "bank": bank
        }
    )

@router.post("/{bank_id}/edit")
def update_bank(

    bank_id: int,

    name: str = Form(...),

    website: str = Form(None),

    logo: str = Form(None),

    status: str = Form(...),

    db: Session = Depends(get_db)

):

    bank = bank_service.get_bank(
        db=db,
        bank_id=bank_id
    )

    bank_data = BankCreate(

        name=name,

        website=website,

        logo=logo,

        status=status

    )

    bank_service.update_bank(
        db=db,
        bank=bank,
        bank_data=bank_data
    )

    return RedirectResponse(
        url="/banks/",
        status_code=303
    )

@router.get("/{bank_id}/delete")
def delete_bank(
    bank_id: int,
    db: Session = Depends(get_db)
):

    bank = bank_service.get_bank(
        db=db,
        bank_id=bank_id
    )

    if bank:

        bank_service.delete_bank(
            db=db,
            bank=bank
        )

    return RedirectResponse(
        url="/banks/",
        status_code=303
    )