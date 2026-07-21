from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    ForeignKey,
    DateTime
)
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base


class LoanRecommendation(Base):

    __tablename__ = "loan_recommendations"

    id = Column(Integer, primary_key=True, index=True)

    customer_name = Column(String)
    age = Column(Integer)
    employment_type = Column(String)
    work_experience_years = Column(Integer)
    monthly_income = Column(Float)
    existing_emi = Column(Float)
    credit_score = Column(Integer)
    loan_amount = Column(Float)
    loan_type = Column(String)
    property_value = Column(Float)
    property_type = Column(String)

    response = Column(Text)


class Bank(Base):

    __tablename__ = "banks"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, unique=True, nullable=False)

    website = Column(String)

    logo = Column(String)

    status = Column(String, default="active")

    contact_email = Column(String, unique=True, nullable=True, index=True)

    # Portal login the agent will use to sign in on the bank's own website in
    # a future automation pass — not wired up to anything yet, storage only.
    # Kept in plaintext (not hashed) because, unlike a user login, the agent
    # needs the actual credential value to type into the bank's real login
    # form, not just a one-way check.
    portal_url = Column(String, nullable=True)

    portal_username = Column(String, nullable=True)

    portal_password = Column(String, nullable=True)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    loan_policies = relationship(
        "BankLoanPolicy",
        back_populates="bank",
        cascade="all, delete-orphan"
    )

    agent_commands = relationship(
        "AgentCommand",
        back_populates="bank",
        cascade="all, delete-orphan"
    )

class BankLoanPolicy(Base):

    __tablename__ = "bank_loan_policies"

    id = Column(Integer, primary_key=True, index=True)

    bank_id = Column(
        Integer,
        ForeignKey("banks.id")
    )

    loan_type = Column(String)

    min_cibil = Column(Integer)

    max_cibil = Column(Integer)

    min_income = Column(Float)

    max_loan_amount = Column(Float)

    interest_rate = Column(Float)

    processing_fee = Column(Float)

    max_ltv = Column(Float)

    min_age = Column(Integer)

    max_age = Column(Integer)

    minimum_work_experience_years = Column(Integer)

    maximum_foir = Column(Float)

    employment_types = Column(Text)

    property_types = Column(Text)

    required_documents = Column(Text)

    special_features = Column(Text)

    prepayment_charges = Column(Text)

    foreclosure_charges = Column(Text)

    min_tenure = Column(Integer)

    max_tenure = Column(Integer)

    last_updated = Column(
        DateTime,
        default=datetime.utcnow
    )

    bank = relationship(
        "Bank",
        back_populates="loan_policies"
    )


class AgentCommand(Base):

    __tablename__ = "agent_commands"

    id = Column(Integer, primary_key=True, index=True)

    # Short name shown in the requirements list, e.g. "Check Rural or Not".
    scenario = Column(String, nullable=False)

    # The actual instruction text handed to the loan-processing agent.
    instruction = Column(Text, nullable=False)

    # None = applies to every loan type; otherwise one of the canonical
    # loan_type values used elsewhere (home_loan, education_loan, ...).
    loan_type = Column(String, nullable=True)

    # None = a global requirement; set = scoped to one specific bank.
    bank_id = Column(
        Integer,
        ForeignKey("banks.id"),
        nullable=True
    )

    # Optional reference file for this requirement (e.g. a sample document
    # the agent should follow). attachment_filename is the randomized name
    # actually stored on disk (backend/static/uploads/requirements/);
    # attachment_original_name is the human-readable name to display/download as.
    attachment_filename = Column(String, nullable=True)

    attachment_original_name = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    bank = relationship(
        "Bank",
        back_populates="agent_commands"
    )