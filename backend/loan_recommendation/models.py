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