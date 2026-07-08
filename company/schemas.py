from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class CompanyBase(BaseModel):
    company_name: str
    company_type: str

    website: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    registration_number: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    cin_number: Optional[str] = None

    industry: Optional[str] = None
    company_size: Optional[str] = None

    incorporation_date: Optional[date] = None

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None

    description: Optional[str] = None
    tags: Optional[str] = None

    status: bool = True


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: int
    logo: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)