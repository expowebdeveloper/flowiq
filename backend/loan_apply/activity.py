"""
Builds a lead's activity log/timeline by reading its Gmail thread live,
rather than from a separate events table — this repo has no per-lead event
log today, and the actual emails (AI's requirements email, the applicant's
reply with attachments, AI's confirmation) already exist in Gmail with real
timestamps/content, so re-deriving a timeline from a written log would just
be a lossy copy of what Gmail already has. Requires UserFormSubmission.
thread_id (set once when the requirements email first opens the thread —
see routes.py's _run_requirements_agent), so leads created before that
column existed have no email history and fall back to just their two
synthetic DB-derived events.
"""
import logging

from auth.oauth import build_gmail_service
from db import BankDecision, get_session
from inbound.extraction import decode_body

logger = logging.getLogger(__name__)


def _find_body_text(payload: dict) -> str:
    """Plain-text body only (never HTML) — this activity log is a compact
    timeline, not a full email reader, so a short readable snippet is more
    useful than rendering formatted HTML inline."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data")
        if data:
            return decode_body(data)
    for part in payload.get("parts", []) or []:
        text = _find_body_text(part)
        if text:
            return text
    return ""


def _list_attachment_filenames(payload: dict) -> list[str]:
    names = []
    if payload.get("filename"):
        names.append(payload["filename"])
    for part in payload.get("parts", []) or []:
        names.extend(_list_attachment_filenames(part))
    return names


def _header(headers: list[dict], name: str) -> str | None:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None


def fetch_thread_events(mailbox_email: str, thread_id: str) -> list[dict]:
    """
    Fetches every message in the Gmail thread and returns one timeline event
    per message: who sent it, when, a body snippet, and any attachment
    filenames. direction is "outbound" when From matches the linked mailbox
    (i.e. sent by us/the AI agent), "inbound" otherwise (the applicant's
    reply) — this is what lets the frontend show who said what without the
    caller needing to know the mailbox address itself.
    """
    service = build_gmail_service(mailbox_email)
    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()

    events = []
    for msg in thread.get("messages", []):
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        from_header = _header(headers, "From") or ""
        to_header = _header(headers, "To") or ""
        subject = _header(headers, "Subject") or ""
        date_header = _header(headers, "Date")

        is_outbound = mailbox_email.lower() in from_header.lower()
        body = _find_body_text(payload).strip()
        attachments = _list_attachment_filenames(payload)

        events.append({
            "type": "email",
            "direction": "outbound" if is_outbound else "inbound",
            "gmail_message_id": msg.get("id"),
            "from": from_header,
            "to": to_header,
            "subject": subject,
            "snippet": msg.get("snippet", ""),
            "body": body,
            "attachments": attachments,
            "date": date_header,
            "internal_date_ms": int(msg["internalDate"]) if msg.get("internalDate") else None,
        })

    events.sort(key=lambda e: e["internal_date_ms"] or 0)
    return events


def get_lead_activity(submission) -> list[dict]:
    """
    Full activity timeline for a UserFormSubmission: a synthetic "lead
    created" event, every email in its Gmail thread (if thread_id/
    mailbox_email were captured), and a synthetic "documents verified" event
    if OCR/verification has completed. Gmail fetch failures are logged and
    swallowed rather than raised — a lead's basic info should still render
    even if the mailbox is temporarily unreachable or was unlinked.
    """
    events = [{
        "type": "lead_created",
        "at_ms": int(submission.created_at.timestamp() * 1000),
        "loan_type": submission.loan_type,
    }]

    if submission.thread_id and submission.mailbox_email:
        try:
            events.extend(fetch_thread_events(submission.mailbox_email, submission.thread_id))
        except Exception:
            logger.exception(
                "loan_apply activity: failed to fetch Gmail thread %s for submission %s",
                submission.thread_id, submission.id,
            )

    if submission.documents_processed_at:
        events.append({
            "type": "documents_processed",
            "at_ms": int(submission.documents_processed_at.timestamp() * 1000),
            "documents_status": submission.documents_status,
        })

    session = get_session()
    try:
        decisions = (
            session.query(BankDecision)
            .filter(BankDecision.submission_id == submission.id)
            .order_by(BankDecision.decided_at.asc())
            .all()
        )
        for decision in decisions:
            events.append({
                "type": "bank_decision",
                "at_ms": int(decision.decided_at.timestamp() * 1000),
                "bank_name": decision.bank_name,
                "status": decision.status,
                "remarks": decision.remarks,
            })
    finally:
        session.close()

    def sort_key(e: dict):
        return e.get("at_ms") if e.get("at_ms") is not None else e.get("internal_date_ms") or 0

    events.sort(key=sort_key)
    return events
