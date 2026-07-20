import os
import io
import json
import base64
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import pdfplumber
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain.prompts import PromptTemplate

from main import build_gmail_service, decode_body, SUPPORTED_MIME_TYPES
from db import is_already_replied, claim_message_for_reply, release_reply_claim

load_dotenv()

# ─── LLM ─────────────────────────────────────────────────────────────────────

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
)

# ─── PDF extractor ────────────────────────────────────────────────────────────

def extract_pdf_text(data: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join(
                page.extract_text() or "" for page in pdf.pages
            ).strip()
    except Exception as e:
        return f"[Could not read PDF: {e}]"


# ─── Email parts extractor with PDF support ───────────────────────────────────

def extract_email_parts(parts: list, service, message_id: str) -> dict:
    body_text = ""
    body_html = ""
    attachments_text = []

    for part in parts:
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        filename = part.get("filename", "")

        if part.get("parts"):
            sub = extract_email_parts(part["parts"], service, message_id)
            body_text = body_text or sub["body_text"]
            body_html = body_html or sub["body_html"]
            attachments_text.extend(sub["attachments_text"])
            continue

        if mime == "text/plain" and not filename:
            body_text = decode_body(body.get("data", ""))
        elif mime == "text/html" and not filename:
            body_html = decode_body(body.get("data", ""))
        elif filename and body.get("attachmentId"):
            att_data = service.users().messages().attachments().get(
                userId="me", messageId=message_id, id=body["attachmentId"]
            ).execute()
            file_bytes = base64.urlsafe_b64decode(att_data["data"] + "==")

            if mime == "application/pdf" or filename.endswith(".pdf"):
                text = extract_pdf_text(file_bytes)
                attachments_text.append(f"[PDF: {filename}]\n{text[:1000]}")
            elif mime == "text/plain":
                attachments_text.append(f"[TXT: {filename}]\n{file_bytes.decode('utf-8', errors='replace')[:2000]}")
            else:
                attachments_text.append(f"[Attachment: {filename} ({mime}) — binary file, cannot read text]")

    return {"body_text": body_text, "body_html": body_html, "attachments_text": attachments_text}


# ─── Tools ───────────────────────────────────────────────────────────────────

def _make_tools(email: str):

    @tool
    def get_unread_emails(max_results: str = "10") -> str:
        """
        Fetch unread emails from Gmail inbox (both with and without attachments).
        Returns a JSON list with id, thread_id, subject, from, to, date, snippet, has_attachment.
        Only emails that have NOT already been replied to are included.
        Use this first to see what emails need replies.
        Action Input: just a number like 10
        """
        service = build_gmail_service(email)
        try:
            limit = min(int(str(max_results).strip()), 5)
        except Exception:
            limit = 5
        result = service.users().messages().list(
            userId="me", maxResults=limit, q="is:unread in:inbox"
        ).execute()
        messages = result.get("messages", [])

        if not messages:
            return json.dumps({"emails": [], "message": "No unread emails found."})

        emails = []
        for msg in messages:
            if is_already_replied(msg["id"]):
                continue
            meta = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in meta.get("payload", {}).get("headers", [])}
            has_attachment = any(
                p.get("filename") for p in meta.get("payload", {}).get("parts", [])
            )
            emails.append({
                "id": msg["id"],
                "thread_id": meta.get("threadId"),
                "subject": headers.get("Subject", "(no subject)"),
                "from": headers.get("From", ""),
                "has_attachment": has_attachment,
            })
        if not emails:
            return json.dumps({"emails": [], "message": "No unread emails found that haven't already been replied to."})
        return json.dumps({"emails": emails}, indent=2)

    @tool
    def read_email(message_id: str) -> str:
        """
        Read full content of an email including body text AND all attachment contents (PDFs, text files).
        Input: message_id string.
        Returns: subject, from, body text, and extracted text from all attachments.
        Always use this before replying so you understand the full context.
        """
        service = build_gmail_service(email)
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        payload = msg.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        parts = payload.get("parts", [])

        if not parts:
            body_data = payload.get("body", {}).get("data", "")
            body_text = decode_body(body_data)
            attachments_text = []
        else:
            extracted = extract_email_parts(parts, service, message_id)
            body_text = extracted["body_text"] or extracted["body_html"]
            attachments_text = extracted["attachments_text"]

        return json.dumps({
            "id": message_id,
            "thread_id": msg.get("threadId"),
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body_text[:800],
            "attachments": attachments_text,
        }, indent=2)

    @tool
    def send_reply(input: str) -> str:
        """
        Send a reply to an email.
        Input must be a JSON string with keys:
          - to: recipient email address
          - subject: subject line
          - body: the full reply text to send
          - thread_id: thread_id from the original email
          - message_id: id from the original email
        Example: {"to": "someone@gmail.com", "subject": "Re: Hello", "body": "Thanks!", "thread_id": "abc", "message_id": "abc"}
        """
        try:
            data = json.loads(input)
        except Exception:
            return "Error: input must be valid JSON with keys: to, subject, body, thread_id, message_id"

        message_id = data.get("message_id")
        if not message_id:
            return "Error: message_id is required so this reply can be tracked and not sent twice."

        if not claim_message_for_reply(message_id, email):
            return f"Skipped: message {message_id} was already replied to. Do not send this reply again."

        service = build_gmail_service(email)
        mime = MIMEMultipart("alternative")
        mime["To"] = data["to"]
        mime["From"] = email
        mime["Subject"] = data["subject"] if data["subject"].startswith("Re:") else f"Re: {data['subject']}"
        mime["In-Reply-To"] = data["message_id"]
        mime["References"] = data["message_id"]
        mime.attach(MIMEText(data["body"], "plain"))

        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        try:
            result = service.users().messages().send(
                userId="me", body={"raw": raw, "threadId": data["thread_id"]}
            ).execute()
        except Exception as e:
            release_reply_claim(message_id)
            return f"Error: failed to send reply, will retry later: {e}"
        return json.dumps({"status": "sent", "message_id": result.get("id")})

    return [get_unread_emails, read_email, send_reply]


# ─── ReAct Prompt ─────────────────────────────────────────────────────────────

REACT_PROMPT = PromptTemplate.from_template("""
You are an intelligent email assistant managing the inbox of {email}.

Your job:
1. Use get_unread_emails to fetch all unread emails
2. For each real personal or business email, use read_email to read the full content including ALL attachments (PDFs, text files)
3. Understand the full context — email body + attachment content combined
4. Write a highly relevant, professional reply based on BOTH the email body AND attachment content
5. Use send_reply to send the reply

Rules:
- get_unread_emails already excludes messages that were already replied to — never call send_reply for a message that wasn't returned by get_unread_emails in this run
- Never call send_reply twice for the same message_id, even across different thoughts/steps
- Always read the full email including attachments before replying
- If the email has a PDF, read its content and base your reply on what the PDF says
- If the email asks a question, answer it based on the attachment content
- If the email shares a document, acknowledge it and summarize what you understood from it
- Be polite, professional, and match the sender's tone
- Keep replies concise (3-6 sentences) unless the content requires more
- SKIP newsletters, promotional emails, and no-reply addresses
- Only reply to real personal or business emails from real people

You have access to the following tools:
{tools}

Use EXACTLY this format:

Question: the input question you must answer
Thought: think about what to do next
Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now know the final answer
Final Answer: summary of all emails processed and replies sent

Begin!

Question: {input}
Thought:{agent_scratchpad}
""")


# ─── Agent Runner ─────────────────────────────────────────────────────────────

def run_email_agent(email: str, task: Optional[str] = None) -> str:
    tools = _make_tools(email)
    agent = create_react_agent(llm=llm, tools=tools, prompt=REACT_PROMPT.partial(email=email))
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=30,
        handle_parsing_errors=True,
    )
    user_task = task or (
        f"Check all unread emails in {email}'s inbox. "
        "For each real personal or business email (not newsletters), "
        "read the full content including all PDF attachments, "
        "understand the context, and send a relevant professional reply."
    )
    result = executor.invoke({"input": user_task})
    return result.get("output", "Agent completed with no output.")
