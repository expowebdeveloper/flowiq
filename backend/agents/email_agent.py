import os
import json
import base64
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
from agents.aadhaar import (
    extract_pdf_text,
    extract_image_text,
    looks_like_aadhaar,
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
    LoanApplicationDocument,
)

load_dotenv()

AADHAAR_APPLICATIONS_DIR = Path("applications")
AADHAAR_APPLICATIONS_DIR.mkdir(exist_ok=True)

# ─── LLM ─────────────────────────────────────────────────────────────────────

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3,
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
        Fetch unread emails from Gmail inbox (both with and without attachments).
        Returns a JSON list with id, thread_id, subject, from, to, date, snippet, has_attachment.
        Only emails that have NOT already been replied to are included.
        Use this first to see what emails need replies.
        Action Input: just a number like 10
        """
        service = build_gmail_service(email)
        try:
            limit = min(int(str(max_results).strip()), 20)
        except Exception:
            limit = 20
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
    def check_aadhaar_and_get_requirements(input: str) -> str:
        """
        Checks whether the email's attachments include a valid-looking Aadhaar card,
        and if so, records the applicant and returns the full list of documents the
        bank still needs for this loan (from the bank's stored requirements).

        Input must be a JSON string with keys:
          - message_id: id from the original email
          - bank_name: the bank the client is asking about (best guess from the email content)
          - loan_type: one of home_loan, education_loan, personal_loan, car_loan, gold_loan
          - applicant_name: sender's name (from the email)
          - applicant_email: sender's email address
          - applicant_phone: phone number if mentioned in the email body, else ""

        Returns JSON with:
          - aadhaar_found: true/false — whether a valid-looking Aadhaar attachment was found
          - required_documents: text of all documents required by the bank for this loan
            (only present when aadhaar_found is true)
        Call this AFTER read_email, once per message, before deciding how to reply.
        """
        try:
            data = json.loads(input)
        except Exception:
            return "Error: input must be valid JSON with keys: message_id, bank_name, loan_type, applicant_name, applicant_email, applicant_phone"

        message_id = data.get("message_id")
        if not message_id:
            return "Error: message_id is required."

        service = build_gmail_service(email)
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        payload = msg.get("payload", {})
        parts = payload.get("parts", [])

        aadhaar_found = False
        aadhaar_filename = None
        aadhaar_bytes = None
        aadhaar_mime = None

        def scan(parts_list):
            nonlocal aadhaar_found, aadhaar_filename, aadhaar_bytes, aadhaar_mime
            for part in parts_list:
                if aadhaar_found:
                    return
                if part.get("parts"):
                    scan(part["parts"])
                    continue
                filename = part.get("filename", "")
                body = part.get("body", {})
                mime = part.get("mimeType", "")
                if not filename or not body.get("attachmentId"):
                    continue
                att_data = service.users().messages().attachments().get(
                    userId="me", messageId=message_id, id=body["attachmentId"]
                ).execute()
                file_bytes = base64.urlsafe_b64decode(att_data["data"] + "==")
                text = ""
                if mime == "application/pdf" or filename.lower().endswith(".pdf"):
                    text = extract_pdf_text(file_bytes)
                elif mime in IMAGE_MIME_TYPES or filename.lower().endswith(IMAGE_EXTENSIONS):
                    text = extract_image_text(file_bytes)
                if looks_like_aadhaar(filename, text):
                    aadhaar_found = True
                    aadhaar_filename = filename
                    aadhaar_bytes = file_bytes
                    aadhaar_mime = mime

        scan(parts)

        if not aadhaar_found:
            return json.dumps({"aadhaar_found": False})

        bank_name = data.get("bank_name", "")
        loan_type = data.get("loan_type", "")

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
                notes=f"Auto-created from inbound email {message_id} by AI agent after Aadhaar verification.",
            )
            session.add(application)
            session.commit()
            session.refresh(application)

            app_dir = AADHAAR_APPLICATIONS_DIR / application.id
            app_dir.mkdir(exist_ok=True)
            doc = LoanApplicationDocument(
                application_id=application.id,
                filename=aadhaar_filename,
                saved_path="",
                content_type=aadhaar_mime,
            )
            session.add(doc)
            session.flush()
            file_path = app_dir / f"{doc.id}_{aadhaar_filename}"
            file_path.write_bytes(aadhaar_bytes)
            doc.saved_path = str(file_path)
            session.commit()

            application_id = application.id
            required_documents = bank_rate.required_documents if bank_rate else None
        finally:
            session.close()

        return json.dumps({
            "aadhaar_found": True,
            "application_id": application_id,
            "required_documents": required_documents or "Please contact us for the full list of required documents.",
        })

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

        service.users().messages().modify(
            userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()

        return json.dumps({"status": "sent", "message_id": result.get("id")})

    return [get_unread_emails, read_email, check_aadhaar_and_get_requirements, send_reply]


# ─── ReAct Prompt ─────────────────────────────────────────────────────────────

REACT_PROMPT = PromptTemplate.from_template("""
You are an intelligent email assistant managing the inbox of {email}.

Your job:
1. Use get_unread_emails to fetch all unread emails
2. For each real personal or business email, use read_email to read the full content including ALL attachments (PDFs, text files)
3. Understand the full context — email body + attachment content combined
4. If the email is a loan inquiry (mentions a bank, loan, applying, interested in a loan, etc.), follow the Loan Inquiry Flow below
5. Otherwise, write a highly relevant, professional reply based on BOTH the email body AND attachment content
6. Use send_reply to send the reply

Loan Inquiry Flow (for emails about applying for a loan):
- Figure out the bank name and loan_type (one of home_loan, education_loan, personal_loan, car_loan, gold_loan) the client is asking about, from the email body/subject
- Call check_aadhaar_and_get_requirements with the message_id, bank_name, loan_type, and the applicant's name/email/phone as best known from the email
- If aadhaar_found is false: reply politely asking the client to share/attach their Aadhaar card, since it is required to proceed with the loan application. Do not say they are approved or eligible.
- If aadhaar_found is true: reply confirming their Aadhaar card was received and verified, then tell them that to proceed further the bank also needs the documents listed in required_documents (include that exact list in the reply)
- Never state a client is fully "eligible" for the loan — only confirm Aadhaar was received/verified and list what else is still needed

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
