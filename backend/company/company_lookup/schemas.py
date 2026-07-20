from pydantic import BaseModel


class CompanyLookupCreate(BaseModel):

    company_name: str

    website: str | None = None

    description: str | None = None

    industry: str | None = None

    emails: list[str] = []

    phones: list[str] = []

    logo: str | None = None

    linkedin: str | None = None

    facebook: str | None = None

    twitter: str | None = None

    instagram: str | None = None

    contact_page: str | None = None

    about_page: str | None = None