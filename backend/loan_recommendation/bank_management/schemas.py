from pydantic import BaseModel


class BankCreate(BaseModel):

    name: str

    website: str | None = None

    logo: str | None = None

    status: str = "active"