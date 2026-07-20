import json
import base64
import secrets
from pathlib import Path
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain.prompts import PromptTemplate

from auth.oauth import build_gmail_service
from inbound.extraction import decode_body
from inbound.threading import apply_threading_headers
from agents.documents import (
    extract_pdf_text,
    extract_image_text,
    IMAGE_MIME_TYPES,
    IMAGE_EXTENSIONS,
)
from db import (
    is_already_replied,
    claim_message_for_reply,
    release_reply_claim,
    get_session,
    User,
    BankLoanRate,
    LoanApplication,
)

load_dotenv()

AADHAAR_APPLICATIONS_DIR = Path("applications")
AADHAAR_APPLICATIONS_DIR.mkdir(exist_ok=True)

# ─── LLM ─────────────────────────────────────────────────────────────────────

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    timeout=120,
)


# ─── Email parts extractor with PDF/image support ─────────────────────────────

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
            elif mime in IMAGE_MIME_TYPES or filename.lower().endswith(IMAGE_EXTENSIONS):
                text = extract_image_text(file_bytes)
                attachments_text.append(f"[Image: {filename}]\n{text[:1000]}")
            elif mime == "text/plain":
                attachments_text.append(f"[TXT: {filename}]\n{file_bytes.decode('utf-8', errors='replace')[:2000]}")
            else:
                attachments_text.append(f"[Attachment: {filename} ({mime}) — binary file, cannot read text]")

    return {"body_text": body_text, "body_html": body_html, "attachments_text": attachments_text}


# ─── Tools ───────────────────────────────────────────────────────────────────

def _make_tools(email: str, broker_id: str):

    @tool
    def get_unread_emails(max_results: str = "10") -> str:
        """
        Fetch recent inbox emails that still need a reply (both with and without attachments).
        Returns a JSON list with id, thread_id, subject, from, to, date, snippet, has_attachment.
        Only emails that have NOT already been replied to are included — this is tracked in
        our own database, independent of Gmail's read/unread state (viewing a message elsewhere,
        e.g. in the Mail UI, does not remove it from this list).
        Use this first to see what emails need replies.
        """
        service = build_gmail_service(email)
        try:
            limit = min(int(str(max_results).strip()), 20)
        except Exception:
            limit = 20
        result = service.users().messages().list(
            userId="me", maxResults=limit, q="in:inbox -in:chats -in:sent newer_than:7d"
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
        message_id = message_id.strip()
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
    def create_loan_application_and_get_required_documents(input: str) -> str:
        """
        Records the applicant's loan inquiry and returns the list of documents required
        for that bank + loan type, so the client can be asked to send them over email.

        Input must be a JSON string with keys:
          - message_id: id from the original email
          - bank_name: the bank the client is asking about (best guess from the email content)
          - loan_type: one of home_loan, education_loan, personal_loan, car_loan, gold_loan
          - applicant_name: sender's name (from the email)
          - applicant_email: sender's email address
          - applicant_phone: phone number if mentioned in the email body, else ""

        Returns JSON with:
          - application_id: the created application's id
          - required_documents: text of all documents required by the bank for this loan —
            list these out for the client in your reply so they know exactly what to send
        Call this AFTER read_email, once per message, before deciding how to reply.
        """
        try:
            data = json.loads(input)
        except Exception:
            return "Error: input must be valid JSON with keys: message_id, bank_name, loan_type, applicant_name, applicant_email, applicant_phone"

        message_id = data.get("message_id", "").strip()
        if not message_id:
            return "Error: message_id is required."

        bank_name = data.get("bank_name", "").strip()
        loan_type = data.get("loan_type", "").strip()

        session = get_session()
        try:
            bank_rate = session.query(BankLoanRate).filter(
                BankLoanRate.bank_name == bank_name, BankLoanRate.loan_type == loan_type
            ).first()

            application = LoanApplication(
                broker_id=broker_id,
                bank_loan_rate_id=bank_rate.id if bank_rate else "",
                bank_name=bank_name,
                loan_type=loan_type,
                applicant_name=data.get("applicant_name", ""),
                applicant_phone=data.get("applicant_phone", ""),
                applicant_email=data.get("applicant_email", ""),
                notes=f"Auto-created from inbound email {message_id} by AI agent.",
                kyc_token=secrets.token_urlsafe(32),
            )
            session.add(application)
            session.commit()
            session.refresh(application)

            application_id = application.id
            required_documents = bank_rate.required_documents if bank_rate else None
        finally:
            session.close()

        return json.dumps({
            "application_id": application_id,
            "required_documents": required_documents or "Please contact us for the full list of required documents.",
        })

    def _send_reply_impl(input: str) -> str:
        try:
            data = json.loads(input)
        except Exception:
            return "Error: input must be valid JSON with keys: to, subject, body, thread_id, message_id"

        message_id = data.get("message_id", "").strip()
        if not message_id:
            return "Error: message_id is required so this reply can be tracked and not sent twice."

        thread_id = data.get("thread_id", "").strip()
        to_addr = data.get("to", "").strip()

        if not claim_message_for_reply(message_id, email):
            return f"Skipped: message {message_id} was already replied to. Do not send this reply again."

        service = build_gmail_service(email)
        mime = MIMEMultipart("alternative")
        mime["To"] = to_addr
        mime["From"] = email
        mime["Subject"] = data["subject"] if data["subject"].startswith("Re:") else f"Re: {data['subject']}"
        # message_id here is the Gmail API message id, not an RFC Message-Id
        # — apply_threading_headers looks up the real header so the reply
        # threads correctly in the RECIPIENT's mailbox too (Gmail threads the
        # SENDER's own view by threadId regardless of headers, which is why
        # this bug is invisible from the sending account).
        apply_threading_headers(mime, service, message_id)
        mime.attach(MIMEText(data["body"], "plain"))

        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        try:
            result = service.users().messages().send(
                userId="me", body={"raw": raw, "threadId": thread_id}
            ).execute()
        except Exception as e:
            release_reply_claim(message_id)
            return f"Error: failed to send reply, will retry later: {e}"

        service.users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()

        return json.dumps({"status": "sent", "message_id": result.get("id")})

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
        return _send_reply_impl(input)

    @tool
    def send_email(input: str) -> str:
        """
        Alias for send_reply — sends a reply to an email. Use send_reply instead
        when possible, but this works identically if called by that name.
        Input must be a JSON string with keys: to, subject, body, thread_id, message_id.
        """
        return _send_reply_impl(input)

    return [
        get_unread_emails,
        read_email,
        create_loan_application_and_get_required_documents,
        send_reply,
        send_email,
    ]


# ─── ReAct Prompt ─────────────────────────────────────────────────────────────

REACT_PROMPT = PromptTemplate.from_template("""
You are an intelligent email assistant managing the inbox of {email}.

Your job:
1. Use get_unread_emails to fetch all unread emails
2. Classify EACH email in the returned list ONE BY ONE using the Classification Rule below — do not judge the list as a whole or assume the whole batch is the same type
3. For each email classified as real, use read_email to read its full content including ALL attachments (PDFs, text files)
4. Understand the full context — email body + attachment content combined
5. If the email is a loan inquiry (mentions a bank, loan, applying, interested in a loan, etc.), follow the Loan Inquiry Flow below
6. Otherwise, write a highly relevant, professional reply based on BOTH the email body AND attachment content
7. Use send_reply to send the reply

Classification Rule (apply per email, not to the batch):
- An email is REAL (must be processed and replied to) if the "from" name/address looks like a person or a company you'd do business with, AND the subject/snippet is not obviously mass marketing.
- An email is a NEWSLETTER/PROMO (skip it) only if it is CLEARLY mass marketing: sent from a brand/product/newsletter address (e.g. "The Batch @ DeepLearning.AI", "Adobe Creative Cloud", growth@, noreply@, hello@mail.*), or the subject is a marketing pitch/digest.
- An email is an AUTOMATED SYSTEM MESSAGE (always skip it, never reply) if it is sent by a mail system rather than a person — e.g. "Mail Delivery Subsystem", mailer-daemon@, postmaster@, any "Delivery Status Notification (Failure)" / bounce / NDR message, or any other automated non-human sender. These are not the same as newsletters, but the rule is identical: skip them and never send a reply, no matter how the subject reads.
- A short or vague subject (e.g. just "loan", "Car Loan", "Finance Related") from what looks like an individual's name and a normal company/personal email address is REAL — never skip it just because the subject is short. When unsure whether one specific email is real or a newsletter, treat it as REAL and process it — only skip the ones that are obviously mass marketing or automated system messages.
- Never make one blanket decision like "all messages in this batch are newsletters" — go through the list and decide per email.

Loan Inquiry Flow (for emails about applying for a loan):
- Figure out the bank name and loan_type (one of home_loan, education_loan, personal_loan, car_loan, gold_loan) the client is asking about, from the email body/subject
- Call create_loan_application_and_get_required_documents with the message_id, bank_name, loan_type, and the applicant's name/email/phone as best known from the email
- Reply politely thanking them for their interest, and clearly list out every document from required_documents, asking them to reply to this email with those documents attached (as PDF or image files, e.g. photos or scans)
- Do NOT send a KYC form link — document collection now happens entirely by the client attaching files directly to their email reply
- Never state a client is fully "approved" or "eligible" for the loan — only confirm their inquiry was received and that you're waiting on their documents

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

CRITICAL: The "Action:" line must contain ONLY the bare tool name — never write arguments,
parentheses, or quotes on that line. Put the argument(s) on the separate "Action Input:" line.

Correct:
Action: get_unread_emails
Action Input: 10

WRONG — never do this:
Action: get_unread_emails(max_results='10')

Begin!

Question: {input}
Thought:{agent_scratchpad}
""")


# ─── Agent Runner ─────────────────────────────────────────────────────────────

def run_email_agent(email: str, task: Optional[str] = None) -> str:
    session = get_session()
    try:
        user = session.query(User).filter(User.email == email).first()
        broker_id = user.id if user else ""
    finally:
        session.close()

    tools = _make_tools(email, broker_id)
    agent = create_react_agent(llm=llm, tools=tools, prompt=REACT_PROMPT.partial(email=email))
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=10,
        max_execution_time=300,
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
