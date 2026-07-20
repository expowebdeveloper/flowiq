import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, UniqueConstraint, Float
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


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bank_name = Column(String, unique=True, nullable=False, index=True)  # matches BankLoanRate.bank_name
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
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
    kyc_token = Column(String, unique=True, nullable=True, index=True)
    credit_score = Column(String, nullable=True)
    kyc_submitted_at = Column(DateTime(timezone=True), nullable=True)
    aadhaar_verified = Column(Boolean, nullable=False, default=False)
    date_of_birth = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    address = Column(Text, nullable=True)


class LoanApplicationDocument(Base):
    __tablename__ = "loan_application_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    saved_path = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    label = Column(String, nullable=True)  # which required document this satisfies, e.g. "PAN card"
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    content_verified = Column(Boolean, nullable=True)  # OCR/content validation result; null = not checked


class RepliedMessage(Base):
    __tablename__ = "replied_messages"

    message_id = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    replied_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class DispatchedMessage(Base):
    """
    Tracks messages that currently have a run_email_agent_for_message task
    in flight (queued or executing), so auto_poll_emails never dispatches a
    second duplicate task for the same message while the first is still
    pending. Distinct from RepliedMessage, which only reflects completed work.
    """
    __tablename__ = "dispatched_messages"

    message_id = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    dispatched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class VerifiedPayload(Base):
    __tablename__ = "verified_payloads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payload_json = Column(Text, nullable=False)
    status = Column(String, nullable=False)  # "verified" or "unverified"
    errors = Column(Text, nullable=True)
    warnings = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class UserFormSubmission(Base):
    __tablename__ = "user_form_submissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # Short, case-sensitive, human-typeable stand-in for `id` (a full UUID)
    # used in the [application id: ...] email subject tag so applicants can
    # copy it into a reply's subject without transcription errors — see
    # loan_apply.agent.generate_short_code/application_id_tag and
    # celery_app.poll_loan_applicant_replies, which looks submissions up by
    # this column when matching an inbound email back to its application.
    short_code = Column(String(8), unique=True, nullable=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone_number = Column(String, nullable=True)  # nullable: submissions made before this field existed have none
    date_of_birth = Column(String, nullable=True)  # ISO date string (YYYY-MM-DD); nullable, see phone_number
    ssn = Column(String, nullable=True)  # Social Security Number; nullable, see phone_number
    gender = Column(String, nullable=False)
    citizenship_status = Column(String, nullable=False)
    current_address = Column(Text, nullable=True)  # nullable: submissions made before this field existed have none
    marital_status = Column(String, nullable=True)  # nullable, see current_address
    loan_type = Column(String, nullable=False)
    fico_score = Column(String, nullable=False)
    zip_code = Column(String, nullable=False)
    loan_amount = Column(Float, nullable=True)
    extra_loan_details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Populated once the applicant emails back their documents and
    # loan_apply.document_processing runs OCR/validation on them.
    documents_status = Column(String, nullable=False, default="awaiting_documents")
    extracted_data = Column(Text, nullable=True)  # JSON: {field_name: value, ...} parsed from OCR text
    documents_processed_at = Column(DateTime(timezone=True), nullable=True)

    # Gmail threadId of the requirements email that opened this applicant's
    # correspondence — set once, when send_requirements_email first sends
    # that email (see loan_apply/routes.py). Used to fetch the full thread
    # (AI's emails + the applicant's replies) for the lead's activity log.
    thread_id = Column(String, nullable=True)
    mailbox_email = Column(String, nullable=True)  # linked Gmail account the thread lives in


class ProcessedApplicantReply(Base):
    """
    Permanently marks a Gmail message_id as having had its document attachments
    processed by loan_apply.document_processing, so poll_loan_applicant_replies
    never reprocesses the same reply on a later poll. Distinct from
    DispatchedMessage, which only tracks a task currently in flight and is
    released once that attempt finishes (success or failure).
    """
    __tablename__ = "processed_applicant_replies"

    message_id = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    processed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class LoanApplyDocument(Base):
    __tablename__ = "loan_apply_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, nullable=False, index=True)
    message_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    saved_path = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    label = Column(String, nullable=True)  # which required document this satisfies, e.g. "PAN Card"
    content_verified = Column(Boolean, nullable=True)  # OCR/content validation result; null = not checked
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class BankNotification(Base):
    """
    In-app notification telling a bank a lead is ready for them to review —
    written once a UserFormSubmission's documents finish verifying (see
    banks.notifications.notify_banks_of_new_lead), targeted at every bank
    that has a BankLoanRate row for that lead's loan_type. One row per
    (submission, bank) pair, read via GET /bank-notifications with
    Depends(require_bank), scoped by the JWT's bank_name.
    """
    __tablename__ = "bank_notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, nullable=False, index=True)
    bank_name = Column(String, nullable=False, index=True)  # matches BankAccount.bank_name
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)


class BankDecision(Base):
    """
    A bank's decision on one loan application (UserFormSubmission), i.e. the
    loan application id. One row per (submission_id, bank_name) pair, same
    key as BankNotification — created/updated via POST
    /bank-notifications/{id}/decision (banks/notification_routes.py) and
    read by GET /bank-decisions. Writing or updating a decision enqueues
    send_bank_decision_update_task (celery_app.py) so the AI agent emails
    the applicant about it in their existing thread.
    """
    __tablename__ = "bank_decisions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, nullable=False, index=True)
    bank_name = Column(String, nullable=False, index=True)  # matches BankAccount.bank_name
    status = Column(String, nullable=False)  # "rejected" | "offer" | "offer_more_documents"
    remarks = Column(Text, nullable=True)  # rejection reason, offer terms, or documents needed
    decided_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    agent_notified_at = Column(DateTime(timezone=True), nullable=True)  # set once the applicant email is sent


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String, nullable=False, index=True)
    recipient_id = Column(String, nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class AgentActivityEvent(Base):
    """
    One row per observable step of AI background processing (mailbox polling,
    OCR/document verification, LLM email composition, sends, bank
    notifications) — written by agent_activity.emit (backend/agent_activity/
    __init__.py) from inside the Celery tasks and the modules they call into
    (loan_apply/document_processing.py, loan_apply/agent.py,
    banks/notifications.py). Read via GET /agent-activity for history on page
    load, and broadcast live over WS /agent-activity/ws as each row is
    written — see agent_activity/routes.py, mirroring how ChatMessage is both
    persisted and pushed live over /chat/ws.
    """
    __tablename__ = "agent_activity_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    source = Column(String, nullable=False)  # e.g. "mailbox_poll", "document_processing", "email_agent", "bank_notify"
    status = Column(String, nullable=False)  # "started" | "info" | "success" | "error"
    message = Column(Text, nullable=False)  # short human-readable summary shown in the feed
    submission_id = Column(String, nullable=True, index=True)  # UserFormSubmission.id, when the event is lead-scoped
    detail = Column(Text, nullable=True)  # JSON blob of extra structured fields, optional


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


def claim_message_for_dispatch(message_id: str, email: str) -> bool:
    """
    Atomically marks a message as having a run_email_agent_for_message task
    in flight. Returns True if this call is the one that claimed it (i.e. it's
    safe to dispatch a task now), False if a task for this message is already
    queued/running from a previous poll.
    """
    session = get_session()
    try:
        stmt = pg_insert(DispatchedMessage).values(
            message_id=message_id, email=email
        ).on_conflict_do_nothing(index_elements=["message_id"])
        result = session.execute(stmt)
        session.commit()
        return result.rowcount > 0
    finally:
        session.close()


def release_dispatch_claim(message_id: str):
    """Call when a dispatched task finishes (success or failure) so the message can be re-dispatched if still unreplied."""
    session = get_session()
    try:
        row = session.get(DispatchedMessage, message_id)
        if row:
            session.delete(row)
            session.commit()
    finally:
        session.close()


def is_applicant_reply_processed(message_id: str) -> bool:
    session = get_session()
    try:
        return session.get(ProcessedApplicantReply, message_id) is not None
    finally:
        session.close()


def mark_applicant_reply_processed(message_id: str, email: str):
    """Permanently marks message_id as processed so poll_loan_applicant_replies never picks it up again."""
    session = get_session()
    try:
        stmt = pg_insert(ProcessedApplicantReply).values(
            message_id=message_id, email=email
        ).on_conflict_do_nothing(index_elements=["message_id"])
        session.execute(stmt)
        session.commit()
    finally:
        session.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
