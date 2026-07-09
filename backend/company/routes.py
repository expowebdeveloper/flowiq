import os
from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from company.schemas import CompanyCreate, CompanyUpdate
from company.services import (
    create_company_service,
    get_all_companies_service,
    get_company_service,
    update_company_service,
    delete_company_service
)

router = APIRouter()

_HERE = os.path.dirname(os.path.abspath(__file__))
_DASH = os.path.join(_HERE, "..", "dashboard", "templates")
templates = Jinja2Templates(directory=[
    os.path.join(_HERE, "templates"),
    os.path.normpath(_DASH)
])


@router.get("/")
def company_list(
    request: Request,
    db: Session = Depends(get_db)
):

    companies = get_all_companies_service(db)

    return templates.TemplateResponse(
        request=request,
        name="company_table.html",
        context={
            "companies": companies
        }
    )

@router.get("/create")
def create_company_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="company_create.html",
        context={}
    )

@router.post("/create")
def create_company(
    company_name: str = Form(...),
    company_type: str = Form(""),

    website: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),

    registration_number: str = Form(""),
    gst_number: str = Form(""),
    pan_number: str = Form(""),
    cin_number: str = Form(""),

    industry: str = Form(""),
    company_size: str = Form(""),

    incorporation_date: str = Form(None),

    address: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    country: str = Form(""),
    postal_code: str = Form(""),

    description: str = Form(""),

    logo_url: str = Form(""),

    tags: str = Form(""),

    status: bool = Form(True),

    logo: UploadFile = File(None),

    db: Session = Depends(get_db)
):

    company = CompanyCreate(
        company_name=company_name,
        company_type=company_type,

        website=website,
        email=email,
        phone=phone,

        registration_number=registration_number,
        gst_number=gst_number,
        pan_number=pan_number,
        cin_number=cin_number,

        industry=industry,
        company_size=company_size,

        incorporation_date=incorporation_date if incorporation_date else None,

        address=address,
        city=city,
        state=state,
        country=country,
        postal_code=postal_code,

        description=description,
        tags=tags,

        status=status
    )

    create_company_service(
        db=db,
        company=company,
        logo=logo,
        logo_url=logo_url
    )

    return RedirectResponse(url="/companies/", status_code=303)

@router.get("/{company_id}")
def company_detail(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    company = get_company_service(
        db,
        company_id
    )

    return templates.TemplateResponse(
        request=request,
        name="company_detail.html",
        context={
            "company": company
        }
    )

@router.get("/{company_id}/edit")
def edit_company_page(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    company = get_company_service(
        db,
        company_id
    )

    return templates.TemplateResponse(
        request=request,
        name="company_form.html",
        context={
            "company": company,
            "is_edit": True
        }
    )

@router.post("/{company_id}/delete")
def delete_company(
    company_id: int,
    db: Session = Depends(get_db)
):

    delete_company_service(
        db,
        company_id
    )

    return JSONResponse(
        {
            "success": True,
            "message": "Company deleted successfully."
        }
    )

@router.post("/{company_id}/edit")
def update_company(
    company_id: int,

    company_name: str = Form(...),
    company_type: str = Form(""),

    website: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),

    registration_number: str = Form(""),
    gst_number: str = Form(""),
    pan_number: str = Form(""),
    cin_number: str = Form(""),

    industry: str = Form(""),
    company_size: str = Form(""),

    incorporation_date: str | None = Form(None),

    address: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    country: str = Form(""),
    postal_code: str = Form(""),

    description: str = Form(""),
    tags: str = Form(""),

    status: bool = Form(True),

    logo: UploadFile | None = File(None),

    db: Session = Depends(get_db),
):


    company = CompanyUpdate(
        company_name=company_name,
        company_type=company_type,

        website=website,
        email=email,
        phone=phone,

        registration_number=registration_number,
        gst_number=gst_number,
        pan_number=pan_number,
        cin_number=cin_number,

        industry=industry,
        company_size=company_size,

        incorporation_date=incorporation_date,

        address=address,
        city=city,
        state=state,
        country=country,
        postal_code=postal_code,

        description=description,
        tags=tags,

        status=status,
    )

    update_company_service(
        db=db,
        company_id=company_id,
        company=company,
        logo=logo,
    )

    return RedirectResponse(url="/companies/", status_code=303)