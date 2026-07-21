from pydantic import BaseModel


class BankCreate(BaseModel):

    name: str

    website: str | None = None

    logo: str | None = None

    status: str = "active"

    contact_email: str | None = None

    portal_url: str | None = None

    portal_username: str | None = None

    portal_password: str | None = None