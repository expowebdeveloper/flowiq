import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in .env")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class GmailToken(Base):
    __tablename__ = "gmail_tokens"

    email = Column(String, primary_key=True)
    credentials_json = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class OAuthVerifier(Base):
    __tablename__ = "oauth_verifiers"

    state = Column(String, primary_key=True)
    code_verifier = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")  # "broker" or "user"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class LoanCategory(Base):
    __tablename__ = "loan_categories"
    __table_args__ = (UniqueConstraint("broker_id", "type", name="uq_broker_loan_type"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    broker_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # home_loan, education_loan, personal_loan, car_loan, gold_loan
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class BankLoanRate(Base):
    __tablename__ = "bank_loan_rates"
    __table_args__ = (UniqueConstraint("bank_name", "loan_type", name="uq_bank_loan_type"),)

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bank_name = Column(String, nullable=False)
    loan_type = Column(String, nullable=False)  # home_loan, education_loan, personal_loan, car_loan, gold_loan
    interest_rate = Column(String, nullable=False)  # e.g. "8.40% - 9.80% p.a."
    details = Column(Text, nullable=True)  # eligibility/tenure notes
    required_documents = Column(Text, nullable=True)  # documents needed to apply/be eligible
    source_url = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    broker_id = Column(String, nullable=False, index=True)
    bank_loan_rate_id = Column(String, nullable=False, index=True)
    bank_name = Column(String, nullable=False)
    loan_type = Column(String, nullable=False)
    applicant_name = Column(String, nullable=False)
    applicant_phone = Column(String, nullable=False)
    applicant_email = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="submitted")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class LoanApplicationDocument(Base):
    __tablename__ = "loan_application_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    saved_path = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    label = Column(String, nullable=True)  # which required document this satisfies, e.g. "PAN card"
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class RepliedMessage(Base):
    __tablename__ = "replied_messages"

    message_id = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    replied_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


def get_session():
    return SessionLocal()


def is_already_replied(message_id: str) -> bool:
    session = get_session()
    try:
        return session.get(RepliedMessage, message_id) is not None
    finally:
        session.close()


def claim_message_for_reply(message_id: str, email: str) -> bool:
    """
    Atomically marks a message as replied. Returns True if this call is the
    one that claimed it (i.e. it's safe to send the reply now), False if
    another process/run already claimed it first.
    """
    session = get_session()
    try:
        stmt = pg_insert(RepliedMessage).values(
            message_id=message_id, email=email
        ).on_conflict_do_nothing(index_elements=["message_id"])
        result = session.execute(stmt)
        session.commit()
        return result.rowcount > 0
    finally:
        session.close()


def release_reply_claim(message_id: str):
    """Undo claim_message_for_reply if the actual send failed, so it can be retried."""
    session = get_session()
    try:
        row = session.get(RepliedMessage, message_id)
        if row:
            session.delete(row)
            session.commit()
    finally:
        session.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
