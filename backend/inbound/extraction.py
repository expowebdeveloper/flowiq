import base64
from pathlib import Path

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
                # Gmail lets multiple attachments on one message share the same
                # filename (e.g. several screenshots all named "image.png") —
                # attachment_id is unique per attachment, so include a short
                # slice of it to avoid one overwriting another on disk.
                safe_name = f"{message_id}_{attachment_id[-10:]}_{filename}"
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
