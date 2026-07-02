import os
import base64
import json
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from db import init_db, get_session, GmailToken, OAuthVerifier

load_dotenv()
init_db()

GOOGLE_CLIENT_ID = os.getenv("client_id")
GOOGLE_CLIENT_SECRET = os.getenv("client_secret")
REDIRECT_URI = "http://localhost:8000/auth/callback"

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError("client_id and client_secret must be set in .env")

# Build the client config dict that Flow accepts directly (no credentials.json needed)
CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uris": [REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

app = FastAPI(title="Email AI - Gmail Inbox Retriever")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

def _pop_verifier(state: str) -> Optional[str]:
    session = get_session()
    try:
        row = session.get(OAuthVerifier, state)
        if not row:
            return None
        code_verifier = row.code_verifier
        session.delete(row)
        session.commit()
        return code_verifier
    finally:
        session.close()


def _save_verifier(state: str, code_verifier: str):
    session = get_session()
    try:
        session.merge(OAuthVerifier(state=state, code_verifier=code_verifier))
        session.commit()
    finally:
        session.close()


ATTACHMENTS_DIR = Path("attachments")
ATTACHMENTS_DIR.mkdir(exist_ok=True)

SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.ms-powerpoint": ".ppt",
    "text/csv": ".csv",
    "application/zip": ".zip",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "text/plain": ".txt",
}


def get_credentials(email: str) -> Optional[Credentials]:
    session = get_session()
    try:
        row = session.get(GmailToken, email)
        if not row:
            return None
        creds = Credentials.from_authorized_user_info(json.loads(row.credentials_json), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            row.credentials_json = creds.to_json()
            session.commit()
        return creds if creds and creds.valid else None
    finally:
        session.close()


def save_credentials(email: str, creds: Credentials):
    session = get_session()
    try:
        session.merge(GmailToken(email=email, credentials_json=creds.to_json()))
        session.commit()
    finally:
        session.close()


def build_gmail_service(email: str):
    creds = get_credentials(email)
    if not creds:
        raise HTTPException(
            status_code=401,
            detail=f"Not authenticated. Visit /auth/link?email={email} to connect your Gmail."
        )
    return build("gmail", "v1", credentials=creds)


def decode_body(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_parts(parts: list, service, user_id: str, message_id: str, email: str) -> dict:
    body_text = ""
    body_html = ""
    attachments = []

    for part in parts:
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        filename = part.get("filename", "")

        if part.get("parts"):
            sub = extract_parts(part["parts"], service, user_id, message_id, email)
            body_text = body_text or sub["body_text"]
            body_html = body_html or sub["body_html"]
            attachments.extend(sub["attachments"])
            continue

        if mime == "text/plain" and not filename:
            body_text = decode_body(body.get("data", ""))
        elif mime == "text/html" and not filename:
            body_html = decode_body(body.get("data", ""))
        elif filename and (mime in SUPPORTED_MIME_TYPES or body.get("attachmentId")):
            attachment_id = body.get("attachmentId")
            if attachment_id:
                att_data = service.users().messages().attachments().get(
                    userId=user_id, messageId=message_id, id=attachment_id
                ).execute()
                file_data = base64.urlsafe_b64decode(att_data["data"] + "==")
                safe_name = f"{message_id}_{filename}"
                user_att_dir = ATTACHMENTS_DIR / email.replace("@", "_at_")
                user_att_dir.mkdir(exist_ok=True)
                file_path = user_att_dir / safe_name
                file_path.write_bytes(file_data)
                attachments.append({
                    "filename": filename,
                    "mime_type": mime,
                    "size_bytes": len(file_data),
                    "download_url": f"/attachments/{email}/{safe_name}",
                    "saved_path": str(file_path),
                })

    return {"body_text": body_text, "body_html": body_html, "attachments": attachments}


# ─── Auth Routes ─────────────────────────────────────────────────────────────

@app.get("/auth/link")
def link_email(email: str = Query(..., description="Gmail address to link")):
    """Start OAuth flow for the given email."""
    import secrets, hashlib, base64 as b64

    code_verifier = secrets.token_urlsafe(64)
    code_challenge = b64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    state = email
    _save_verifier(state, code_verifier)

    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        login_hint=email,
        prompt="consent",
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
def auth_callback(code: str, state: str):
    """OAuth callback — saves token for the linked email."""
    try:
        code_verifier = _pop_verifier(state)

        flow = Flow.from_client_config(
            CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
            state=state,
        )
        import os as _os
        _os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
        flow.fetch_token(code=code, code_verifier=code_verifier)
        creds = flow.credentials

        user_info_service = build("oauth2", "v2", credentials=creds)
        user_info = user_info_service.userinfo().get().execute()
        actual_email = user_info.get("email", state)

        save_credentials(actual_email, creds)
        return RedirectResponse(f"http://localhost:5173/?linked=1&email={actual_email}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")


@app.get("/auth/status")
def auth_status(email: str = Query(...)):
    """Check if an email is linked."""
    creds = get_credentials(email)
    return {"email": email, "linked": creds is not None}


# ─── Inbox Routes ─────────────────────────────────────────────────────────────

@app.get("/inbox")
def get_inbox(
    email: str = Query(..., description="Linked Gmail address"),
    max_results: int = Query(20, le=100, description="Max emails to fetch"),
    page_token: Optional[str] = Query(None, description="Pagination token"),
    query: str = Query("in:inbox", description="Gmail search query"),
):
    """Retrieve inbox emails with metadata (no body/attachments)."""
    service = build_gmail_service(email)

    params = {
        "userId": "me",
        "maxResults": max_results,
        "q": query,
    }
    if page_token:
        params["pageToken"] = page_token

    result = service.users().messages().list(**params).execute()
    messages = result.get("messages", [])
    next_page = result.get("nextPageToken")

    email_list = []
    for msg in messages:
        meta = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()

        headers = {h["name"]: h["value"] for h in meta.get("payload", {}).get("headers", [])}
        has_attachment = any(
            p.get("filename") for p in meta.get("payload", {}).get("parts", [])
        )

        email_list.append({
            "id": msg["id"],
            "thread_id": meta.get("threadId"),
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From"),
            "to": headers.get("To"),
            "date": headers.get("Date"),
            "snippet": meta.get("snippet", ""),
            "has_attachment": has_attachment,
            "labels": meta.get("labelIds", []),
        })

    return {
        "email": email,
        "total_fetched": len(email_list),
        "next_page_token": next_page,
        "messages": email_list,
    }


@app.get("/inbox/message/{message_id}")
def get_message(
    message_id: str,
    email: str = Query(..., description="Linked Gmail address"),
    download_attachments: bool = Query(True, description="Download attachments to disk"),
):
    """Retrieve full email content including body and all attachments."""
    service = build_gmail_service(email)

    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()

    payload = msg.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

    parts = payload.get("parts", [])
    # Single-part message (no parts list)
    if not parts:
        body_data = payload.get("body", {}).get("data", "")
        body_text = decode_body(body_data) if payload.get("mimeType") == "text/plain" else ""
        body_html = decode_body(body_data) if payload.get("mimeType") == "text/html" else ""
        attachments = []
    else:
        extracted = extract_parts(
            parts, service, "me", message_id, email if download_attachments else "__dry__"
        )
        body_text = extracted["body_text"]
        body_html = extracted["body_html"]
        attachments = extracted["attachments"] if download_attachments else []

    return {
        "id": message_id,
        "thread_id": msg.get("threadId"),
        "subject": headers.get("Subject", "(no subject)"),
        "from": headers.get("From"),
        "to": headers.get("To"),
        "cc": headers.get("Cc"),
        "date": headers.get("Date"),
        "snippet": msg.get("snippet", ""),
        "body_text": body_text,
        "body_html": body_html,
        "labels": msg.get("labelIds", []),
        "attachments": attachments,
    }


@app.get("/inbox/full")
def get_full_inbox(
    email: str = Query(..., description="Linked Gmail address"),
    max_results: int = Query(10, le=50, description="Max emails (with full content)"),
    query: str = Query("in:inbox", description="Gmail search query"),
    download_attachments: bool = Query(True),
):
    """Fetch inbox emails WITH full body and attachments in one call."""
    service = build_gmail_service(email)

    result = service.users().messages().list(
        userId="me", maxResults=max_results, q=query, labelIds=["INBOX"]
    ).execute()
    messages = result.get("messages", [])

    emails = []
    for msg in messages:
        full = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()

        payload = full.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        parts = payload.get("parts", [])

        if not parts:
            body_data = payload.get("body", {}).get("data", "")
            body_text = decode_body(body_data) if "text/plain" in payload.get("mimeType", "") else ""
            body_html = decode_body(body_data) if "text/html" in payload.get("mimeType", "") else ""
            attachments = []
        else:
            user_email = email if download_attachments else "__dry__"
            extracted = extract_parts(parts, service, "me", msg["id"], user_email)
            body_text = extracted["body_text"]
            body_html = extracted["body_html"]
            attachments = extracted["attachments"] if download_attachments else []

        emails.append({
            "id": msg["id"],
            "thread_id": full.get("threadId"),
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From"),
            "to": headers.get("To"),
            "date": headers.get("Date"),
            "snippet": full.get("snippet", ""),
            "body_text": body_text,
            "body_html": body_html,
            "labels": full.get("labelIds", []),
            "attachments": attachments,
        })

    return {
        "email": email,
        "total_fetched": len(emails),
        "emails": emails,
    }


# ─── Send Email ──────────────────────────────────────────────────────────────

from pydantic import BaseModel
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class SendEmailRequest(BaseModel):
    email: str          # sender (linked account)
    to: str
    subject: str
    body: str
    reply_to_message_id: Optional[str] = None
    thread_id: Optional[str] = None
    cc: Optional[str] = None

@app.post("/send")
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
        mime["In-Reply-To"] = req.reply_to_message_id
        mime["References"]  = req.reply_to_message_id

    mime.attach(MIMEText(req.body, "plain"))

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    body: dict = {"raw": raw}
    if req.thread_id:
        body["threadId"] = req.thread_id

    result = service.users().messages().send(userId="me", body=body).execute()
    return {"message_id": result.get("id"), "thread_id": result.get("threadId"), "status": "sent"}


# ─── Attachment Download ──────────────────────────────────────────────────────

@app.get("/attachments/{email}/{filename}")
def download_attachment(email: str, filename: str):
    """Download a previously saved attachment."""
    safe_email = email.replace("@", "_at_")
    file_path = ATTACHMENTS_DIR / safe_email / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(str(file_path), filename=filename)


# ─── Agent Routes ─────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    email: str
    task: Optional[str] = None  # custom instruction, or leave empty for default

@app.post("/agent/run")
def run_agent(req: AgentRequest):
    """Trigger the email agent to read and reply to emails (runs in background via Celery)."""
    from celery_app import run_email_agent_task
    job = run_email_agent_task.delay(req.email, req.task)
    return {"task_id": job.id, "status": "started", "message": "Agent is running in background."}

@app.get("/agent/status/{task_id}")
def agent_status(task_id: str):
    """Check the status of a running agent task."""
    from celery_app import celery
    job = celery.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": job.status,
        "result": job.result if job.ready() else None,
    }


# ─── Utility ──────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "Email AI - Gmail Inbox Retriever",
        "endpoints": {
            "1. Link email (OAuth)": "GET /auth/link?email=you@gmail.com",
            "2. Check auth status": "GET /auth/status?email=you@gmail.com",
            "3. List inbox (fast)": "GET /inbox?email=you@gmail.com&max_results=20",
            "4. Get single email + attachments": "GET /inbox/message/{id}?email=you@gmail.com",
            "5. Full inbox with bodies": "GET /inbox/full?email=you@gmail.com&max_results=10",
            "6. Download attachment": "GET /attachments/{email}/{filename}",
            "docs": "/docs",
        }
    }
