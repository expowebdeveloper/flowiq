from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from auth.oauth import build_gmail_service
from inbound.extraction import ATTACHMENTS_DIR, decode_body, extract_parts

router = APIRouter(tags=["inbox"])


@router.get("/inbox")
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


def _parse_message(msg: dict, service, email: str, download_attachments: bool) -> dict:
    """Shared full-message parsing used by both /inbox/message/{id} and
    /inbox/thread/{thread_id} so a single message is represented identically
    whether fetched standalone or as part of a thread."""
    message_id = msg["id"]
    payload = msg.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

    parts = payload.get("parts", [])
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


@router.get("/inbox/message/{message_id}")
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

    return _parse_message(msg, service, email, download_attachments)


@router.get("/inbox/thread/{thread_id}")
def get_thread(
    thread_id: str,
    email: str = Query(..., description="Linked Gmail address"),
    download_attachments: bool = Query(True, description="Download attachments to disk"),
):
    """Retrieve every message in a Gmail thread (full body + attachments each),
    oldest first, so the frontend can render one applicant conversation as a
    single threaded view instead of separate rows per reply."""
    service = build_gmail_service(email)

    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()
    messages = thread.get("messages", [])
    # Gmail already returns thread messages in chronological order, but sort
    # defensively by internalDate so this holds even if that ever changes.
    messages.sort(key=lambda m: int(m.get("internalDate", 0)))

    parsed = [_parse_message(msg, service, email, download_attachments) for msg in messages]

    return {
        "email": email,
        "thread_id": thread_id,
        "total_messages": len(parsed),
        "messages": parsed,
    }


@router.get("/inbox/full")
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


@router.get("/attachments/{email}/{filename}", tags=["attachments"])
def download_attachment(email: str, filename: str):
    """Download a previously saved attachment."""
    safe_email = email.replace("@", "_at_")
    file_path = ATTACHMENTS_DIR / safe_email / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(str(file_path), filename=filename)
