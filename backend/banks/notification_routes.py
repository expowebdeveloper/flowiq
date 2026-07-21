from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from auth import require_bank
from banks.pdf import build_applicant_pdf
from db import BankDecision, BankNotification, LoanApplyDocument, UserFormSubmission, get_session
from loan_apply.schemas import LoanApplyDocumentOut

router = APIRouter(prefix="/bank-notifications", tags=["bank-notifications"])

DECISION_STATUSES = {"rejected", "offer", "offer_more_documents"}


class DecisionIn(BaseModel):
    status: str = Field(..., description="One of: rejected, offer, offer_more_documents")
    remarks: str | None = None


def _serialize(
    notification: BankNotification,
    submission: UserFormSubmission | None,
    decision: BankDecision | None = None,
) -> dict:
    return {
        "id": notification.id,
        "submission_id": notification.submission_id,
        "created_at": notification.created_at.isoformat(),
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        # Submission can be None if the lead was deleted after notifying —
        # surfaced as null lead fields rather than dropping the notification
        # row, so a bank never sees a silently-vanishing unread count.
        "applicant_name": f"{submission.first_name} {submission.last_name}" if submission else None,
        "applicant_email": submission.email if submission else None,
        "loan_type": submission.loan_type if submission else None,
        "loan_amount": submission.loan_amount if submission else None,
        "fico_score": int(submission.fico_score) if submission and submission.fico_score else None,
        "decision": _serialize_decision(decision) if decision else None,
    }


def _serialize_decision(decision: BankDecision) -> dict:
    return {
        "id": decision.id,
        "status": decision.status,
        "remarks": decision.remarks,
        "decided_at": decision.decided_at.isoformat(),
        "agent_notified_at": decision.agent_notified_at.isoformat() if decision.agent_notified_at else None,
    }


@router.get("")
def list_bank_notifications(current_user: dict = Depends(require_bank)):
    """
    Notifications for the current bank: one per lead whose documents finished
    verifying and who requested a loan_type this bank offers (see
    banks.notifications.notify_banks_of_new_lead for how these are written).
    Newest first.
    """
    session = get_session()
    try:
        notifications = (
            session.query(BankNotification)
            .filter(BankNotification.bank_name == current_user["bank_name"])
            .order_by(BankNotification.created_at.desc())
            .all()
        )
        submission_ids = {n.submission_id for n in notifications}
        submissions = {
            s.id: s
            for s in session.query(UserFormSubmission).filter(UserFormSubmission.id.in_(submission_ids))
        } if submission_ids else {}
        decisions = {
            d.submission_id: d
            for d in session.query(BankDecision).filter(
                BankDecision.bank_name == current_user["bank_name"],
                BankDecision.submission_id.in_(submission_ids),
            )
        } if submission_ids else {}

        result = [
            _serialize(n, submissions.get(n.submission_id), decisions.get(n.submission_id))
            for n in notifications
        ]
        unread_count = sum(1 for n in notifications if n.read_at is None)
        return {"count": len(result), "unread_count": unread_count, "notifications": result}
    finally:
        session.close()


@router.post("/{notification_id}/decision")
def record_decision(notification_id: str, payload: DecisionIn, current_user: dict = Depends(require_bank)):
    """
    Records (or updates) the current bank's decision — reject, offer, or
    offer_more_documents — on the loan application (UserFormSubmission,
    identified by the notification's submission_id) behind this
    notification, then hands it off to the AI agent, which emails the
    applicant about it in their existing thread (see
    celery_app.send_bank_decision_update_task).
    """
    if payload.status not in DECISION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of: {', '.join(sorted(DECISION_STATUSES))}",
        )

    session = get_session()
    try:
        notification = session.get(BankNotification, notification_id)
        if not notification or notification.bank_name != current_user["bank_name"]:
            raise HTTPException(status_code=404, detail="Notification not found")

        decision = (
            session.query(BankDecision)
            .filter(
                BankDecision.submission_id == notification.submission_id,
                BankDecision.bank_name == current_user["bank_name"],
            )
            .first()
        )
        now = datetime.now(timezone.utc)
        if decision:
            decision.status = payload.status
            decision.remarks = payload.remarks
            decision.decided_at = now
            decision.agent_notified_at = None  # re-notify the applicant about the updated decision
        else:
            decision = BankDecision(
                submission_id=notification.submission_id,
                bank_name=current_user["bank_name"],
                status=payload.status,
                remarks=payload.remarks,
                decided_at=now,
            )
            session.add(decision)
        session.commit()
        session.refresh(decision)

        decision_id = decision.id
        result = _serialize_decision(decision)
    finally:
        session.close()

    from celery_app import send_bank_decision_update_task
    send_bank_decision_update_task.delay(decision_id)

    return result


@router.post("/{notification_id}/read")
def mark_notification_read(notification_id: str, current_user: dict = Depends(require_bank)):
    """Marks one of the current bank's notifications as read."""
    session = get_session()
    try:
        notification = session.get(BankNotification, notification_id)
        if not notification or notification.bank_name != current_user["bank_name"]:
            raise HTTPException(status_code=404, detail="Notification not found")
        if notification.read_at is None:
            notification.read_at = datetime.now(timezone.utc)
            session.commit()
        return {"id": notification.id, "read_at": notification.read_at.isoformat()}
    finally:
        session.close()


@router.post("/read-all")
def mark_all_notifications_read(current_user: dict = Depends(require_bank)):
    """Marks every unread notification for the current bank as read."""
    session = get_session()
    try:
        now = datetime.now(timezone.utc)
        updated = (
            session.query(BankNotification)
            .filter(
                BankNotification.bank_name == current_user["bank_name"],
                BankNotification.read_at.is_(None),
            )
            .update({BankNotification.read_at: now}, synchronize_session=False)
        )
        session.commit()
        return {"updated_count": updated}
    finally:
        session.close()


@router.get("/{notification_id}/pdf")
def get_notification_pdf(notification_id: str, current_user: dict = Depends(require_bank)):
    """
    Renders the applicant's full details (personal info, loan details,
    extracted fields, and document checklist) as a PDF, scoped to a
    notification belonging to the current bank.
    """
    session = get_session()
    try:
        notification = session.get(BankNotification, notification_id)
        if not notification or notification.bank_name != current_user["bank_name"]:
            raise HTTPException(status_code=404, detail="Notification not found")
        submission_id = notification.submission_id
    finally:
        session.close()

    try:
        pdf_bytes = build_applicant_pdf(submission_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Applicant details are no longer available")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="applicant-{submission_id}.pdf"'},
    )


def _submission_id_for_bank_notification(notification_id: str, bank_name: str) -> str:
    """
    Resolves notification_id -> its submission_id, scoped to the current
    bank — same check as get_notification_pdf above, so a bank can only ever
    reach documents for a lead it was actually notified about (not any
    submission_id in the system, which is what letting the bank call
    loan_apply's require_broker-only document routes directly would allow).
    """
    session = get_session()
    try:
        notification = session.get(BankNotification, notification_id)
        if not notification or notification.bank_name != bank_name:
            raise HTTPException(status_code=404, detail="Notification not found")
        return notification.submission_id
    finally:
        session.close()


@router.get("/{notification_id}/documents", response_model=list[LoanApplyDocumentOut])
def list_notification_documents(notification_id: str, current_user: dict = Depends(require_bank)):
    """
    Every document attachment the applicant behind this notification has
    sent in so far — mirrors loan_apply.routes.list_loan_apply_documents,
    but scoped to notification_id/the current bank rather than
    require_broker, since a bank has no broker JWT to call that route with.
    """
    submission_id = _submission_id_for_bank_notification(notification_id, current_user["bank_name"])

    session = get_session()
    try:
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


@router.get("/{notification_id}/documents/{document_id}")
def download_notification_document(
    notification_id: str,
    document_id: str,
    disposition: str = "attachment",
    current_user: dict = Depends(require_bank),
):
    """
    Serves one document from the applicant behind this notification —
    mirrors loan_apply.routes.download_loan_apply_document, scoped to
    notification_id/the current bank (see _submission_id_for_bank_notification).
    """
    if disposition not in ("attachment", "inline"):
        raise HTTPException(status_code=400, detail="disposition must be 'attachment' or 'inline'")

    submission_id = _submission_id_for_bank_notification(notification_id, current_user["bank_name"])

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
