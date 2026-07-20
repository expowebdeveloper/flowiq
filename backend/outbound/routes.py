import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from auth.oauth import build_gmail_service
from inbound.threading import apply_threading_headers

router = APIRouter(tags=["email"])


class SendEmailRequest(BaseModel):
    email: str          # sender (linked account)
    to: str
    subject: str
    body: str
    reply_to_message_id: Optional[str] = None
    thread_id: Optional[str] = None
    cc: Optional[str] = None


@router.post("/send")
def send_email(req: SendEmailRequest):
    """Send or reply to an email."""
    service = build_gmail_service(req.email)

    mime = MIMEMultipart("alternative")
    mime["To"]      = req.to
    mime["From"]    = req.email
    mime["Subject"] = req.subject
    if req.cc:
        mime["Cc"] = req.cc
    if req.reply_to_message_id:
        # reply_to_message_id is a Gmail API message id, not an RFC
        # Message-Id — apply_threading_headers looks up the real header so
        # the reply threads correctly in the RECIPIENT's mailbox too (Gmail
        # threads the SENDER's own view by threadId regardless of headers,
        # which is why this bug is invisible from the sending account).
        apply_threading_headers(mime, service, req.reply_to_message_id)

    mime.attach(MIMEText(req.body, "plain"))

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    body: dict = {"raw": raw}
    if req.thread_id:
        body["threadId"] = req.thread_id

    result = service.users().messages().send(userId="me", body=body).execute()
    return {"message_id": result.get("id"), "thread_id": result.get("threadId"), "status": "sent"}
