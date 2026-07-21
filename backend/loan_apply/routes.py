import json
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from auth import require_broker
from db import BankDecision, LoanApplyDocument, UserFormSubmission, get_session
from .activity import get_lead_activity
from .agent import send_requirements_email
from .schemas import BankDecisionOut, LoanApplyCreate, LoanApplyDocumentOut, LoanApplyOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/loan-apply", tags=["loan-apply"])


@router.get("/requirements")
def get_requirements():
    from .requirements import load_requirements
    try:
        reqs = load_requirements()
        return reqs.get("loan_category_requirements", {})
    except Exception as e:
        logger.exception("Failed to load requirements")
        return {}


def _annual_income_verified(session, submission_id: str) -> bool | None:
    """
    True if the most recently received "Annual Income" document passed its
    content_verified check (structurally valid AND its certified figure
    matched extra_loan_details.annual_income — see
    loan_apply.document_processing.process_loan_applicant_reply); False if
    one was received but failed; None if none has been received yet. Only
    the latest one counts, so a corrected resend after a mismatch clears the
    earlier failure once it verifies.
    """
    doc = (
        session.query(LoanApplyDocument)
        .filter(LoanApplyDocument.submission_id == submission_id, LoanApplyDocument.label == "Annual Income")
        .order_by(LoanApplyDocument.uploaded_at.desc())
        .first()
    )
    return doc.content_verified if doc else None


def _to_out(session, record: UserFormSubmission, decisions: list[BankDecision] = ()) -> LoanApplyOut:
    return LoanApplyOut(
        id=record.id,
        first_name=record.first_name,
        last_name=record.last_name,
        email=record.email,
        phone_number=record.phone_number,
        date_of_birth=record.date_of_birth,
        ssn=record.ssn,
        gender=record.gender,
        citizenship_status=record.citizenship_status,
        current_address=record.current_address,
        marital_status=record.marital_status,
        loan_type=record.loan_type,
        fico_score=int(record.fico_score),
        zip_code=record.zip_code,
        loan_amount=record.loan_amount if record.loan_amount is not None else 0.0,
        extra_loan_details=json.loads(record.extra_loan_details) if record.extra_loan_details else None,
        created_at=record.created_at.isoformat(),
        documents_status=record.documents_status,
        extracted_data=json.loads(record.extracted_data) if record.extracted_data else None,
        documents_processed_at=record.documents_processed_at.isoformat() if record.documents_processed_at else None,
        bank_decisions=[
            BankDecisionOut(
                bank_name=d.bank_name, status=d.status, remarks=d.remarks, decided_at=d.decided_at.isoformat()
            )
            for d in decisions
        ],
        annual_income_verified=_annual_income_verified(session, record.id),
    )


def _run_requirements_agent(submission_id: str, applicant_name: str, applicant_email: str, loan_type: str):
    logger.info(
        "loan_apply agent: starting for %s (%s, loan_type=%s)",
        applicant_email, applicant_name, loan_type,
    )
    try:
        result = send_requirements_email(applicant_name, applicant_email, loan_type, submission_id=submission_id)
        logger.info(
            "loan_apply agent: sent message_id=%s to %s from %s (category=%s)",
            result["message_id"], result["recipient_email"], result["sender_email"], result["loan_category"],
        )
        # Persisted so the lead's activity log can later fetch this Gmail
        # thread directly (see GET /loan-apply/{id}/activity) — this is the
        # thread-opening email, so its threadId is the whole conversation's.
        session = get_session()
        try:
            record = session.get(UserFormSubmission, submission_id)
            if record:
                record.thread_id = result["thread_id"]
                record.mailbox_email = result["sender_email"]
                session.commit()
        finally:
            session.close()
    except Exception:
        logger.exception("loan_apply agent: failed to send requirements email to %s", applicant_email)


@router.post("", response_model=LoanApplyOut)
def submit_loan_apply(payload: LoanApplyCreate, background_tasks: BackgroundTasks):
    logger.info(
        "loan_apply: form submitted by %s %s <%s>, loan_type=%s",
        payload.first_name, payload.last_name, payload.email, payload.loan_type,
    )
    session = get_session()
    try:
        record = UserFormSubmission(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            phone_number=payload.phone_number,
            date_of_birth=payload.date_of_birth,
            ssn=payload.ssn,
            gender=payload.gender,
            citizenship_status=payload.citizenship_status,
            current_address=payload.current_address,
            marital_status=payload.marital_status,
            loan_type=payload.loan_type,
            fico_score=str(payload.fico_score),
            zip_code=payload.zip_code,
            loan_amount=payload.loan_amount,
            extra_loan_details=json.dumps(payload.extra_loan_details) if payload.extra_loan_details else None,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        out = _to_out(session, record)
    finally:
        session.close()

    logger.info("loan_apply: submission %s saved, queuing agent to run in background", out.id)
    background_tasks.add_task(
        _run_requirements_agent,
        out.id,
        f"{payload.first_name} {payload.last_name}",
        payload.email,
        payload.loan_type,
    )
    return out


@router.get("/applicant-emails", response_model=list[str])
def list_applicant_emails(current_user: dict = Depends(require_broker)):
    """Distinct email addresses of everyone who has submitted the loan-apply form, used to scope the Mail inbox/sent views to applicant correspondence only."""
    session = get_session()
    try:
        rows = session.query(UserFormSubmission.email).distinct().all()
        return [r[0] for r in rows]
    finally:
        session.close()


@router.get("", response_model=list[LoanApplyOut])
def list_loan_apply_submissions(current_user: dict = Depends(require_broker)):
    session = get_session()
    try:
        records = (
            session.query(UserFormSubmission)
            .order_by(UserFormSubmission.created_at.desc())
            .all()
        )
        submission_ids = [r.id for r in records]
        decisions_by_submission: dict[str, list[BankDecision]] = {}
        if submission_ids:
            decision_rows = (
                session.query(BankDecision)
                .filter(BankDecision.submission_id.in_(submission_ids))
                .order_by(BankDecision.decided_at.desc())
            )
            for d in decision_rows:
                decisions_by_submission.setdefault(d.submission_id, []).append(d)
        return [_to_out(session, r, decisions_by_submission.get(r.id, [])) for r in records]
    finally:
        session.close()


@router.get("/{submission_id}/activity")
def get_loan_apply_activity(submission_id: str, current_user: dict = Depends(require_broker)):
    """
    Full activity timeline for a lead: lead-created, every email in the
    Gmail thread (AI's requirements email, the applicant's reply with
    attachments, AI's follow-ups), and documents-processed — see
    activity.get_lead_activity for how these are assembled.
    """
    session = get_session()
    try:
        record = session.get(UserFormSubmission, submission_id)
        if not record:
            raise HTTPException(status_code=404, detail="Submission not found")
        return {"events": get_lead_activity(record)}
    finally:
        session.close()


@router.get("/{submission_id}", response_model=LoanApplyOut)
def get_loan_apply_submission(submission_id: str, current_user: dict = Depends(require_broker)):
    session = get_session()
    try:
        record = session.get(UserFormSubmission, submission_id)
        if not record:
            raise HTTPException(status_code=404, detail="Submission not found")
        decisions = (
            session.query(BankDecision)
            .filter(BankDecision.submission_id == submission_id)
            .order_by(BankDecision.decided_at.desc())
            .all()
        )
        return _to_out(session, record, decisions)
    finally:
        session.close()


@router.get("/{submission_id}/documents", response_model=list[LoanApplyDocumentOut])
def list_loan_apply_documents(submission_id: str, current_user: dict = Depends(require_broker)):
    """
    Every document attachment received from this lead across all of their
    replies so far — accumulates automatically as loan_apply.document_processing
    persists each new LoanApplyDocument row on every reply, so this list
    naturally grows from e.g. 5 documents to all 10 as the applicant sends
    the rest, with no separate "finalize" step.
    """
    session = get_session()
    try:
        if not session.get(UserFormSubmission, submission_id):
            raise HTTPException(status_code=404, detail="Submission not found")
        docs = (
            session.query(LoanApplyDocument)
            .filter(LoanApplyDocument.submission_id == submission_id)
            .order_by(LoanApplyDocument.uploaded_at.asc())
            .all()
        )
        return [
            LoanApplyDocumentOut(
                id=d.id,
                filename=d.filename,
                content_type=d.content_type,
                label=d.label,
                content_verified=d.content_verified,
                uploaded_at=d.uploaded_at.isoformat(),
            )
            for d in docs
        ]
    finally:
        session.close()


@router.get("/{submission_id}/documents/{document_id}")
def download_loan_apply_document(
    submission_id: str,
    document_id: str,
    disposition: str = "attachment",
    current_user: dict = Depends(require_broker),
):
    """
    Serves one document a lead sent in, mirroring
    banks.applications.download_application_document. disposition=inline
    (vs. the default "attachment") tells the browser to render the file —
    image/PDF — in place instead of forcing a save-as, used by the lead
    profile's document "view" action; download still uses "attachment" so
    it always saves regardless of file type.
    """
    if disposition not in ("attachment", "inline"):
        raise HTTPException(status_code=400, detail="disposition must be 'attachment' or 'inline'")

    session = get_session()
    try:
        doc = session.get(LoanApplyDocument, document_id)
        if not doc or doc.submission_id != submission_id:
            raise HTTPException(status_code=404, detail="Document not found")

        file_path = Path(doc.saved_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        return FileResponse(str(file_path), filename=doc.filename, content_disposition_type=disposition)
    finally:
        session.close()
