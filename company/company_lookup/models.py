from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import DateTime
from sqlalchemy.sql import func

from db import Base


class CompanyLookup(Base):

    __tablename__ = "company_lookup"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    company_name = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    website = Column(String)

    description = Column(Text)

    industry = Column(String)

    emails = Column(Text)

    phones = Column(Text)

    logo = Column(String)

    linkedin = Column(String)

    facebook = Column(String)

    twitter = Column(String)

    instagram = Column(String)

    contact_page = Column(String)

    about_page = Column(String)

    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )