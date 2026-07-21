import base64
import html
import logging
import re
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from langchain_groq import ChatGroq

from agent_activity import emit
from auth.oauth import build_gmail_service
from db import GmailToken, get_session
from inbound.threading import apply_threading_headers
from .requirements import get_required_documents

logger = logging.getLogger(__name__)

# Short, case-sensitive, human-typeable stand-in for a submission's real UUID
# (see db.UserFormSubmission.short_code) — embedded in every loan_apply
# email's subject (see application_id_tag below) so an applicant's reply
# carries it back to us even if they compose a brand-new message instead of
# hitting Reply. Gmail's "Re:" on a genuine reply keeps the original subject
# (and thus this tag) intact; a new message only matches if the applicant
# copies the tag in themselves. celery_app.poll_loan_applicant_replies
# extracts this with APPLICATION_ID_RE and looks it up by short_code.
#
# Alphabet excludes visually-ambiguous characters (0/O, 1/I/l) since this is
# meant to be read off an email and typed back in; case sensitivity is what
# keeps 8 characters from that reduced alphabet still collision-resistant
# enough for this use (57^8 ≈ 1.1×10^14 possibilities).
SHORT_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
SHORT_CODE_LENGTH = 8
APPLICATION_ID_RE = re.compile(r"\[application id:\s*([0-9A-Za-z]{8})\]", re.IGNORECASE)

# Fallback for when an applicant types/pastes the bare code without the
# brackets our own emails send (e.g. "application id: nJAiByz2", or just
# "nJAiByz2" on its own) — matches any standalone 8-character token from the
# same alphanumeric charset, word-bounded so it doesn't grab a substring out
# of a longer word. This is intentionally loose: on its own an 8-char token
# could be any random word, so extract_candidate_codes() never treats a match
# here as authoritative — see its docstring and the caller in
# celery_app.poll_loan_applicant_replies, which only accepts a candidate that
# also resolves to a real UserFormSubmission.short_code.
BARE_CODE_RE = re.compile(r"\b[0-9A-Za-z]{8}\b")


def generate_short_code() -> str:
    return "".join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(SHORT_CODE_LENGTH))


def application_id_tag(short_code: str, subject: str) -> str:
    return f"[application id: {short_code}] {subject}"


def extract_application_id(text: str) -> str | None:
    """
    Pulls the first `[application id: <code>]` tag's code out of a subject or
    body, or None if absent. The code itself is returned exactly as matched
    (case preserved) — matching against db.UserFormSubmission.short_code must
    be an exact, case-sensitive comparison, never case-insensitive, since the
    alphabet was chosen specifically so upper/lower variants are both valid
    distinct codes.
    """
    match = APPLICATION_ID_RE.search(text or "")
    return match.group(1) if match else None


def extract_candidate_codes(text: str) -> list[str]:
    """
    Every plausible application-id code in `text`, most-confident first: the
    bracketed [application id: ...] tag (if present) always comes first,
    followed by every standalone 8-character alphanumeric token found
    anywhere (see BARE_CODE_RE) — covers an applicant typing/pasting just the
    bare code without the brackets, e.g. copying "your application ID is
    nJAiByz2" out of the requirements email body.
    Order matters: no ranking beyond "the real tag wins over a loose
    guess" — none of these are trusted as a real match on their own. The
    caller (celery_app.poll_loan_applicant_replies) must check each against
    UserFormSubmission.short_code and use the first that actually resolves.
    """
    tagged = extract_application_id(text)
    bare = BARE_CODE_RE.findall(text or "")
    seen = set()
    candidates = []
    for code in ([tagged] if tagged else []) + bare:
        if code not in seen:
            seen.add(code)
            candidates.append(code)
    return candidates

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    timeout=120,
)

REQUIREMENTS_INTRO_PROMPT = """You are a loan assistant writing an email to a loan applicant.

Applicant name: {applicant_name}
Loan type requested: {loan_category}

Write ONLY a short, friendly, professional greeting and opening paragraph (1-2 sentences) telling
the applicant that to proceed with their {loan_category} application, you need them to send over
the documents listed below. Do NOT write out the document names or a list yourself, and do NOT
write a closing/sign-off line — both will be appended separately after your text. Do not mention
any portal, website, or a different email address. Do not add pricing, interest rate, or approval
promises.

Write only that opening paragraph (no subject line, no markdown, no document list, no closing).
"""

MISSING_DOCUMENTS_INTRO_PROMPT = """You are a loan assistant writing a follow-up email to a loan applicant
who already replied to their {loan_category} application requirements email, but their application
is still incomplete.

Applicant name: {applicant_name}

Write ONLY a short, friendly, professional opening that:
1. Thanks them generically for their reply (e.g. "thank you for getting back to us") — do NOT
   claim to have received any specific named document, since you have not been told which (if
   any) of their attachments were successfully verified.
2. Tells them we still need the documents listed below. Do NOT write out the document names or
   a list yourself — the list will be inserted separately after your text.
3. {unclear_instruction}
Do NOT mention any portal, website, or a different email address to send documents to, since
none exists. Do not add pricing, interest rate, or approval promises. Do NOT write a closing/
sign-off line or a "reply to this email" instruction — both will be appended separately.

Write only that opening (no subject line, no markdown, no document list, no closing).
"""

DOCUMENT_REMINDER_INTRO_PROMPT = """You are a loan assistant sending an automated reminder to a loan applicant
who has not sent all the documents required for their {loan_category} application. This is reminder
#{reminder_number} of {max_reminders} — no reply has been received since the last message.

Applicant name: {applicant_name}

Write ONLY a short, polite, professional opening that:
1. Reminds them their {loan_category} application is still on hold pending the documents listed below.
   Do NOT write out the document names or a list yourself — the list will be inserted separately.
2. {escalation_instruction}
Do NOT mention any portal, website, or a different email address to send documents to, since none
exists. Do not add pricing, interest rate, or approval promises. Do NOT write a closing/sign-off
line or a "reply to this email" instruction — both will be appended separately.

Write only that opening (no subject line, no markdown, no document list, no closing).
"""

_REMINDER_ESCALATION_NORMAL = "Keep the tone light and helpful, as an early reminder."
_REMINDER_ESCALATION_FINAL = (
    "Mention this is the final automated reminder, and that if the documents aren't received, "
    "someone from the team will follow up with them directly."
)


ANNUAL_INCOME_MISMATCH_PROMPT = """You are a loan assistant writing a follow-up email to a loan applicant
who has sent in an Annual Income verification document for their {loan_category} application, but the
certified income figure on that document does not match the annual income they declared on their
application.

Applicant name: {applicant_name}

Write ONLY a short, polite, professional message that:
1. Thanks them for sending the Annual Income document.
2. Explains that the certified income figure on the document they sent does not match the annual
   income declared on their application, so it could not be verified.
3. Asks them to please resend a correct, valid Annual Income verification document that matches the
   income they declared.
Do NOT state either figure or number yourself — do not invent or repeat specific amounts. Do NOT say
the document is fake, fraudulent, or invalid in general — only that the figures do not match. Do NOT
mention any portal, website, or a different email address to send documents to, since none exists. Do
not add pricing, interest rate, or approval promises. Do NOT write a closing/sign-off line or a "reply
to this email" instruction — both will be appended separately.

Write only that message (no subject line, no markdown, no closing).
"""


MISSING_APPLICATION_ID_PROMPT = """You are a loan assistant writing an email to someone who emailed in
about their loan application, but you could not tell which application it belongs to.

Write ONLY a short, friendly, professional message that:
1. Thanks them for getting in touch.
2. Explains that you could not find their application ID in this message, so you're unable to match
   it to their application yet.
3. Asks them to please reply with their application ID included, or reply directly to the original
   "Required documents" email instead of starting a new one.
Do NOT mention any portal, website, or a different email address. Do not add pricing, interest rate,
or approval promises. Do NOT write a closing/sign-off line — it will be appended separately.

Write only that message (no subject line, no markdown, no closing).
"""

DECISION_PROMPTS = {
    "rejected": """You are a loan assistant writing an email to a loan applicant informing them that
{bank_name} has reviewed their {loan_category} application and decided not to move forward with it.

Applicant name: {applicant_name}
Bank remarks (may be empty): {remarks}

Write a short, polite, professional email that:
1. Clearly but kindly states that {bank_name} is unable to offer this loan at this time.
2. If bank remarks are given, incorporate the reason in plain language; if empty, do not invent one.
3. Does NOT discourage them from hearing from other banks that may still be reviewing their
   application, if any are.
Do not add pricing, interest rate, or approval promises. Do NOT write a closing/sign-off line —
it will be appended separately.

Write only the email body text (no subject line, no markdown, no closing).
""",
    "offer": """You are a loan assistant writing an email to a loan applicant informing them that
{bank_name} has made them an offer on their {loan_category} application.

Applicant name: {applicant_name}
Offer details from the bank (may be empty): {remarks}

Write a short, friendly, professional email that:
1. Congratulates them and states that {bank_name} has approved/offered them the loan.
2. If offer details are given, relay them in plain language; if empty, tell them to expect the
   bank to follow up shortly with full terms — do not invent numbers.
3. Tells them to expect further contact from the bank for next steps.
Do NOT write a closing/sign-off line — it will be appended separately.

Write only the email body text (no subject line, no markdown, no closing).
""",
    "offer_more_documents": """You are a loan assistant writing an email to a loan applicant informing them
that {bank_name} is willing to offer them a loan for their {loan_category} application, but needs
more documents or information before finalizing it.

Applicant name: {applicant_name}

Write ONLY a short, friendly, professional opening that tells them {bank_name} is interested in
offering them the loan, but needs some additional documents or information first. Do NOT write out
what is needed yourself — that will be inserted separately, verbatim, right after your text, exactly
as the bank specified it. Do NOT write a closing/sign-off line or a "reply to this email"
instruction — both will be appended separately.

Write only that opening (no subject line, no markdown, no closing).
""",
}

DECISION_SUBJECTS = {
    "rejected": "Update on your {loan_category} application — {bank_name}",
    "offer": "Good news on your {loan_category} application — {bank_name}",
    "offer_more_documents": "Action needed on your {loan_category} application — {bank_name}",
}


DOCUMENTS_COMPLETE_PROMPT = """You are a loan assistant writing an email to a loan applicant
who has just sent in the last of their required documents for their {loan_category} application.

Applicant name: {applicant_name}

Write a short, friendly, professional email that:
1. Confirms all required documents have now been received.
2. Tells them the documents are now being verified/processed, and that they will be contacted
   with an update once verification is complete.
Do NOT mention any portal, website, or a different email address. Do not add pricing, interest
rate, or approval promises — this is only a receipt confirmation, not an approval decision.

Write only the email body text (no subject line, no markdown).
"""

_UNCLEAR_INSTRUCTION_WITH_ATTACHMENTS = (
    "Also add a short paragraph mentioning that {unclear_count} of the file(s) they sent could "
    "not be read clearly (e.g. blurry, low resolution, or an unsupported format) — ask them to "
    "resend those specific document(s) as a clearer, well-lit photo or scan. Do NOT say the "
    "documents are invalid or wrong — say they could not be read clearly and ask for a clearer "
    "copy. Do NOT list document names for this — that will be inserted separately."
)
_UNCLEAR_INSTRUCTION_NONE = "Do not mention unclear or unreadable files, since none were received."


_REPLY_INSTRUCTION = "Simply reply to this email with the documents attached."
_SIGN_OFF = "Best regards,\nLoan Assistant"


def _render_numbered_documents(documents: list) -> str:
    """
    Renders a document list as a plain numbered list ("1. Aadhaar Card —
    description", "2. PAN Card — description", ...) — built here in Python
    rather than left to the LLM, since asking an LLM to both write free-form
    prose AND hold a strict list format consistently is unreliable in
    practice (observed output folded the list into narrative paragraphs
    instead of keeping it scannable). This guarantees the exact same,
    reliably formatted list on every email regardless of model output.
    """
    if not documents:
        return "(none)"
    lines = []
    for i, doc in enumerate(documents, start=1):
        description = doc.get("description")
        if description:
            lines.append(f"{i}. {doc['document']} — {description}")
        else:
            lines.append(f"{i}. {doc['document']}")
    return "\n".join(lines)


def _get_sender_email() -> str:
    session = get_session()
    try:
        token = session.query(GmailToken).first()
        if not token:
            raise RuntimeError("No linked Gmail account found. Link one via /auth/link first.")
        return token.email
    finally:
        session.close()


def _get_latest_thread_message_id(sender_email: str, thread_id: str) -> str | None:
    """
    Returns the Gmail API message id of the most recent message in thread_id,
    for use as in_reply_to_message_id. Reminders aren't a reply to any one
    specific inbound message (see send_document_reminder_email), but without
    real In-Reply-To/References headers a reminder only threads correctly in
    the SENDER's own mailbox (Gmail groups by threadId there regardless of
    headers) — every other client, including the applicant's own Gmail,
    threads by chasing those headers (see inbound.threading's module
    docstring) and would show each reminder as a new, disconnected thread.
    Chaining off whatever the last message actually is (applicant's or our
    own) keeps every reminder in that same real thread for the recipient too.
    Returns None if the thread can't be fetched (caller should just omit
    threading headers rather than fail the send).
    """
    try:
        service = build_gmail_service(sender_email)
        thread = (
            service.users()
            .threads()
            .get(userId="me", id=thread_id, format="minimal")
            .execute()
        )
        messages = thread.get("messages", [])
        if not messages:
            return None
        return messages[-1]["id"]
    except Exception:
        logger.exception("loan_apply agent: failed to fetch latest message in thread %s", thread_id)
        return None


def build_requirements_email_body(applicant_name: str, loan_type: str, short_code: str) -> tuple[str, dict]:
    info = get_required_documents(loan_type)
    logger.info(
        "loan_apply agent: resolved loan_type=%r -> category=%r (%d general docs, %d category docs)",
        loan_type, info["category"], len(info["general_documents"]), len(info["category_documents"]),
    )

    prompt = REQUIREMENTS_INTRO_PROMPT.format(
        applicant_name=applicant_name or "Applicant",
        loan_category=info["category"],
    )

    logger.info("loan_apply agent: composing email body with LLM (llama-3.3-70b-versatile)...")
    response = llm.invoke(prompt)
    intro = response.content if hasattr(response, "content") else str(response)
    intro = intro.strip()
    logger.info("loan_apply agent: LLM composed intro (%d chars)", len(intro))

    # The numbered document list is rendered here in Python (see
    # _render_numbered_documents), not by the LLM, so its format is exact
    # and consistent on every email rather than whatever the model happens
    # to produce for a "list documents" instruction embedded in free prose.
    all_documents = info["general_documents"] + info["category_documents"]
    document_list = _render_numbered_documents(all_documents)
    application_id_note = (
        f"Your application ID is {short_code}. If you reply to this email directly, you don't need to "
        "do anything else — but if you send a new email instead of replying, please keep "
        f"\"[application id: {short_code}]\" at the start of the subject line exactly as shown, so we can "
        "match it to your application. It is case-sensitive."
    )
    body = (
        f"{intro}\n\n{document_list}\n\n{_REPLY_INSTRUCTION}\n\n{application_id_note}\n\n{_SIGN_OFF}"
    )

    return body, info


_REMINDER_HTML_BANNER = (
    "<div style=\"background:#fff8e1;border-left:4px solid #f5a623;padding:10px 14px;"
    "margin-bottom:16px;font-family:Arial, sans-serif;font-size:13px;color:#7a5b00;\">"
    "&#128337; <strong>Reminder {reminder_number} of {max_reminders}</strong> — automated follow-up, "
    "no reply received since our last message.</div>"
)


def _body_to_html(body: str, html_banner: str | None = None) -> str:
    """
    Converts a plain-text email body (built from `\\n`-joined paragraphs, see
    build_requirements_email_body et al.) into HTML with explicit <br>/<p>
    tags, for the "text/html" alternative part _send_email attaches alongside
    the plain-text one.

    Plain text alone leaves line-wrapping up to whichever client renders it:
    Gmail's own Sent view (same account reading its own message) tends to
    preserve single line breaks, but many receiving clients collapse them and
    only honor blank-line paragraph breaks — which folded every numbered
    document list into one run-together paragraph for the recipient, even
    though it looked correctly formatted to the sender. An explicit HTML part
    renders identically everywhere regardless of how a client treats
    plain-text wrapping.

    html_banner, if given, is raw HTML (already-formatted, not escaped)
    inserted before the body content, replacing the plain-text body's own
    leading "[Reminder N of M ...]" bracketed line (see
    build_document_reminder_email_body) so the reminder marker isn't shown
    twice — once as a styled callout, once as its plain-text equivalent.
    """
    paragraphs = body.split("\n\n")
    if html_banner and paragraphs and paragraphs[0].startswith("["):
        paragraphs = paragraphs[1:]
    html_paragraphs = [
        "<p>" + html.escape(paragraph).replace("\n", "<br>") + "</p>"
        for paragraph in paragraphs
    ]
    return (
        "<html><body style=\"font-family: Arial, sans-serif; font-size: 14px; "
        "white-space: normal;\">" + (html_banner or "") + "".join(html_paragraphs) + "</body></html>"
    )


def _send_email(
    sender_email: str,
    applicant_email: str,
    subject: str,
    body: str,
    thread_id: str | None = None,
    in_reply_to_message_id: str | None = None,
    submission_id: str | None = None,
    html_banner: str | None = None,
) -> dict:
    service = build_gmail_service(sender_email)
    mime = MIMEMultipart("alternative")
    mime["To"] = applicant_email
    mime["From"] = sender_email
    mime["Subject"] = subject
    if in_reply_to_message_id:
        # in_reply_to_message_id is a Gmail API message id, not an RFC
        # Message-Id — apply_threading_headers looks up the real header so
        # the reply threads correctly in the RECIPIENT's mailbox too (Gmail
        # threads the SENDER's own view by threadId regardless of headers,
        # which is why this bug was invisible from the sending account).
        apply_threading_headers(mime, service, in_reply_to_message_id)
    # Both parts carry the same content — text/plain first, then text/html,
    # per RFC 2046's requirement that "multipart/alternative" parts be
    # ordered from least to most preferred so an HTML-capable client renders
    # the html part instead of falling back to plain text.
    mime.attach(MIMEText(body, "plain"))
    mime.attach(MIMEText(_body_to_html(body, html_banner=html_banner), "html"))

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    send_body = {"raw": raw}
    if thread_id:
        send_body["threadId"] = thread_id

    result = service.users().messages().send(userId="me", body=send_body).execute()

    # Single choke point every loan_apply email send goes through, so one
    # emit() call here covers requirements/missing-documents/documents-
    # complete/decision-update emails without repeating it at each call site.
    emit("email_agent", "success", f"Sent \"{subject}\" to {applicant_email}", submission_id=submission_id)

    return {"message_id": result.get("id"), "thread_id": result.get("threadId")}


def _get_or_create_short_code(submission_id: str) -> str:
    """
    Returns the submission's short_code, generating and persisting one first
    if it doesn't have one yet (e.g. rows created before this column existed —
    see the b7d3f2a8c1e9 migration, which backfills those in bulk, but new
    rows created via the ORM default get theirs here). Retries on a rare
    UNIQUE collision, per generate_short_code's small but non-zero collision
    chance across many submissions.
    """
    from db import UserFormSubmission

    session = get_session()
    try:
        submission = session.get(UserFormSubmission, submission_id)
        if submission.short_code:
            return submission.short_code
        for _ in range(5):
            code = generate_short_code()
            submission.short_code = code
            try:
                session.commit()
                return code
            except Exception:
                session.rollback()
        raise RuntimeError(f"Could not generate a unique short_code for submission {submission_id}")
    finally:
        session.close()


def send_requirements_email(
    applicant_name: str, applicant_email: str, loan_type: str, submission_id: str
) -> dict:
    """
    Composes (via LLM) and sends an email to applicant_email listing the
    required documents for loan_type, from the first linked Gmail account.
    The subject is prefixed with a [application id: <short_code>] tag (see
    application_id_tag) so a reply — even a brand-new message rather than a
    same-thread Reply — can be matched back to this submission; see
    celery_app.poll_loan_applicant_replies.
    """
    short_code = _get_or_create_short_code(submission_id)
    body, info = build_requirements_email_body(applicant_name, loan_type, short_code)
    sender_email = _get_sender_email()
    logger.info("loan_apply agent: sending from %s to %s", sender_email, applicant_email)

    sent = _send_email(
        sender_email, applicant_email,
        subject=application_id_tag(short_code, f"Required documents for your {info['category']} application"),
        body=body,
        submission_id=submission_id,
    )

    return {
        "message_id": sent["message_id"],
        "thread_id": sent["thread_id"],
        "sender_email": sender_email,
        "recipient_email": applicant_email,
        "loan_category": info["category"],
        "body": body,
    }


def build_missing_documents_email_body(
    applicant_name: str, loan_category: str, missing_documents: list, unclear_count: int = 0
) -> str:
    if unclear_count > 0:
        unclear_instruction = _UNCLEAR_INSTRUCTION_WITH_ATTACHMENTS.format(unclear_count=unclear_count)
    else:
        unclear_instruction = _UNCLEAR_INSTRUCTION_NONE

    prompt = MISSING_DOCUMENTS_INTRO_PROMPT.format(
        applicant_name=applicant_name or "Applicant",
        loan_category=loan_category,
        unclear_instruction=unclear_instruction,
    )
    logger.info(
        "loan_apply agent: composing missing-documents follow-up with LLM (llama-3.3-70b-versatile), unclear_count=%d...",
        unclear_count,
    )
    response = llm.invoke(prompt)
    intro = response.content if hasattr(response, "content") else str(response)
    intro = intro.strip()
    logger.info("loan_apply agent: LLM composed missing-documents intro (%d chars)", len(intro))

    # Same rationale as build_requirements_email_body: the numbered list is
    # rendered deterministically in Python rather than left to the LLM.
    document_list = _render_numbered_documents(missing_documents)
    body = f"{intro}\n\n{document_list}\n\n{_REPLY_INSTRUCTION}\n\n{_SIGN_OFF}"
    return body


def send_missing_documents_email(
    applicant_name: str,
    applicant_email: str,
    loan_category: str,
    missing_documents: list,
    thread_id: str,
    in_reply_to_message_id: str,
    unclear_count: int = 0,
    submission_id: str | None = None,
) -> dict:
    """
    Composes (via LLM) and sends a follow-up email listing the documents not
    yet received, plus (if any) a note that some sent files couldn't be read
    clearly and should be resent — threaded as a reply to the applicant's
    original message so it stays in the same conversation.
    """
    body = build_missing_documents_email_body(applicant_name, loan_category, missing_documents, unclear_count)
    sender_email = _get_sender_email()
    logger.info("loan_apply agent: sending missing-documents follow-up from %s to %s", sender_email, applicant_email)

    subject = f"Re: Required documents for your {loan_category} application"
    if submission_id:
        subject = application_id_tag(_get_or_create_short_code(submission_id), subject)

    sent = _send_email(
        sender_email, applicant_email,
        subject=subject,
        body=body,
        thread_id=thread_id,
        in_reply_to_message_id=in_reply_to_message_id,
        submission_id=submission_id,
    )

    return {
        "message_id": sent["message_id"],
        "sender_email": sender_email,
        "recipient_email": applicant_email,
        "loan_category": loan_category,
        "missing_documents": [d["document"] for d in missing_documents],
        "unclear_count": unclear_count,
        "body": body,
    }


def build_annual_income_mismatch_email_body(applicant_name: str, loan_category: str) -> str:
    prompt = ANNUAL_INCOME_MISMATCH_PROMPT.format(
        applicant_name=applicant_name or "Applicant",
        loan_category=loan_category,
    )
    logger.info("loan_apply agent: composing annual-income-mismatch follow-up with LLM (llama-3.3-70b-versatile)...")
    response = llm.invoke(prompt)
    intro = response.content if hasattr(response, "content") else str(response)
    intro = intro.strip()
    logger.info("loan_apply agent: LLM composed annual-income-mismatch body (%d chars)", len(intro))

    document_list = _render_numbered_documents([{"document": "Annual Income"}])
    body = f"{intro}\n\n{document_list}\n\n{_REPLY_INSTRUCTION}\n\n{_SIGN_OFF}"
    return body


def send_annual_income_mismatch_email(
    applicant_name: str,
    applicant_email: str,
    loan_category: str,
    declared_annual_income: str,
    thread_id: str,
    in_reply_to_message_id: str,
    submission_id: str | None = None,
) -> dict:
    """
    Composes (via LLM) and sends a follow-up email telling the applicant their
    Annual Income document's certified figure doesn't match the annual income
    they declared on their application — threaded as a reply to the
    applicant's original message. Called by
    loan_apply.document_processing.process_loan_applicant_reply once it
    detects the mismatch; declared_annual_income is accepted for logging/
    the return value only, never included in the email body itself (see
    ANNUAL_INCOME_MISMATCH_PROMPT, which explicitly forbids stating figures).
    """
    body = build_annual_income_mismatch_email_body(applicant_name, loan_category)
    sender_email = _get_sender_email()
    logger.info(
        "loan_apply agent: sending annual-income-mismatch follow-up from %s to %s", sender_email, applicant_email
    )

    subject = f"Re: Required documents for your {loan_category} application"
    if submission_id:
        subject = application_id_tag(_get_or_create_short_code(submission_id), subject)

    sent = _send_email(
        sender_email, applicant_email,
        subject=subject,
        body=body,
        thread_id=thread_id,
        in_reply_to_message_id=in_reply_to_message_id,
        submission_id=submission_id,
    )

    return {
        "message_id": sent["message_id"],
        "sender_email": sender_email,
        "recipient_email": applicant_email,
        "loan_category": loan_category,
        "declared_annual_income": declared_annual_income,
        "body": body,
    }


MAX_DOCUMENT_REMINDERS = 3


def build_document_reminder_email_body(
    applicant_name: str, loan_category: str, missing_documents: list, reminder_number: int
) -> str:
    escalation_instruction = (
        _REMINDER_ESCALATION_FINAL if reminder_number >= MAX_DOCUMENT_REMINDERS else _REMINDER_ESCALATION_NORMAL
    )
    prompt = DOCUMENT_REMINDER_INTRO_PROMPT.format(
        applicant_name=applicant_name or "Applicant",
        loan_category=loan_category,
        reminder_number=reminder_number,
        max_reminders=MAX_DOCUMENT_REMINDERS,
        escalation_instruction=escalation_instruction,
    )
    logger.info(
        "loan_apply agent: composing document reminder #%d/%d with LLM (llama-3.3-70b-versatile)...",
        reminder_number, MAX_DOCUMENT_REMINDERS,
    )
    response = llm.invoke(prompt)
    intro = response.content if hasattr(response, "content") else str(response)
    intro = intro.strip()
    logger.info("loan_apply agent: LLM composed reminder intro (%d chars)", len(intro))

    document_list = _render_numbered_documents(missing_documents)
    banner = f"[Reminder {reminder_number} of {MAX_DOCUMENT_REMINDERS} — automated follow-up]"
    body = f"{banner}\n\n{intro}\n\n{document_list}\n\n{_REPLY_INSTRUCTION}\n\n{_SIGN_OFF}"
    return body


def send_document_reminder_email(
    applicant_name: str,
    applicant_email: str,
    loan_category: str,
    missing_documents: list,
    reminder_number: int,
    thread_id: str | None,
    submission_id: str,
) -> dict:
    """
    Composes (via LLM) and sends one automated "you still haven't sent all
    your documents" reminder — see celery_app.send_missing_document_reminders,
    which calls this at most MAX_DOCUMENT_REMINDERS times per lead, spaced
    ~10 minutes apart, then stops (the broker takes over from there).
    Threaded into the applicant's existing conversation when a thread_id is
    available: Gmail's threadId keeps it grouped in the SENDER's own mailbox
    regardless of headers, but the applicant's own mail client threads by
    chasing the real In-Reply-To/References header chain (see
    inbound.threading's module docstring) — so this also looks up the
    thread's latest message via _get_latest_thread_message_id and replies to
    it, even though a reminder isn't "in reply to" any one specific inbound
    message. Without that, every reminder showed up as a brand-new,
    disconnected thread in the applicant's inbox instead of staying in the
    original conversation.
    """
    body = build_document_reminder_email_body(applicant_name, loan_category, missing_documents, reminder_number)
    sender_email = _get_sender_email()
    logger.info(
        "loan_apply agent: sending document reminder #%d from %s to %s",
        reminder_number, sender_email, applicant_email,
    )

    # Same base subject text as send_missing_documents_email/
    # send_documents_complete_email ("Re: Required documents for your ...")
    # rather than distinct wording ("Reminder: documents still needed...") —
    # Gmail's inbox LIST view (as opposed to a thread's own detail view,
    # which correctly follows In-Reply-To/References regardless of subject)
    # additionally weighs subject-line similarity when deciding whether to
    # group a message with the rest of its conversation, so a subject that
    # diverges enough from the rest of the thread can show up as a separate
    # top-level row there even though it's the same underlying Gmail thread.
    # The "this is a reminder" framing already lives in the body/HTML banner
    # (see build_document_reminder_email_body, _REMINDER_HTML_BANNER).
    subject = application_id_tag(
        _get_or_create_short_code(submission_id),
        f"Re: Required documents for your {loan_category} application",
    )

    in_reply_to_message_id = _get_latest_thread_message_id(sender_email, thread_id) if thread_id else None

    html_banner = _REMINDER_HTML_BANNER.format(
        reminder_number=reminder_number, max_reminders=MAX_DOCUMENT_REMINDERS,
    )

    sent = _send_email(
        sender_email, applicant_email,
        subject=subject,
        body=body,
        thread_id=thread_id,
        in_reply_to_message_id=in_reply_to_message_id,
        submission_id=submission_id,
        html_banner=html_banner,
    )

    return {
        "message_id": sent["message_id"],
        "sender_email": sender_email,
        "recipient_email": applicant_email,
        "loan_category": loan_category,
        "reminder_number": reminder_number,
        "missing_documents": [d["document"] for d in missing_documents],
        "body": body,
    }


def build_missing_application_id_email_body(applicant_name: str) -> str:
    prompt = MISSING_APPLICATION_ID_PROMPT.format(applicant_name=applicant_name or "Applicant")
    logger.info("loan_apply agent: composing missing-application-id reply with LLM (llama-3.3-70b-versatile)...")
    response = llm.invoke(prompt)
    body = response.content if hasattr(response, "content") else str(response)
    body = body.strip()
    body = f"{body}\n\n{_SIGN_OFF}"
    logger.info("loan_apply agent: LLM composed missing-application-id body (%d chars)", len(body))
    return body


def send_missing_application_id_email(
    applicant_name: str,
    applicant_email: str,
    subject: str,
    thread_id: str | None = None,
    in_reply_to_message_id: str | None = None,
) -> dict:
    """
    Disabled: this helper used to send the missing-application-id auto-reply.
    The poller now marks those messages processed without outbound email.
    """
    logger.info(
        "loan_apply agent: skipped disabled missing-application-id reply to %s", applicant_email
    )
    return {
        "status": "skipped",
        "reason": "missing_application_id_auto_reply_disabled",
        "recipient_email": applicant_email,
    }


def build_documents_complete_email_body(applicant_name: str, loan_category: str) -> str:
    prompt = DOCUMENTS_COMPLETE_PROMPT.format(
        applicant_name=applicant_name or "Applicant",
        loan_category=loan_category,
    )
    logger.info("loan_apply agent: composing documents-complete confirmation with LLM (llama-3.3-70b-versatile)...")
    response = llm.invoke(prompt)
    body = response.content if hasattr(response, "content") else str(response)
    body = body.strip()
    logger.info("loan_apply agent: LLM composed documents-complete body (%d chars)", len(body))
    return body


def send_documents_complete_email(
    applicant_name: str,
    applicant_email: str,
    loan_category: str,
    thread_id: str,
    in_reply_to_message_id: str,
    submission_id: str | None = None,
) -> dict:
    """
    Composes (via LLM) and sends a confirmation email once all required
    documents for the applicant's loan have been received and verified —
    threaded as a reply to the applicant's original message.
    """
    body = build_documents_complete_email_body(applicant_name, loan_category)
    sender_email = _get_sender_email()
    logger.info("loan_apply agent: sending documents-complete confirmation from %s to %s", sender_email, applicant_email)

    subject = f"Re: Required documents for your {loan_category} application"
    if submission_id:
        subject = application_id_tag(_get_or_create_short_code(submission_id), subject)

    sent = _send_email(
        sender_email, applicant_email,
        subject=subject,
        body=body,
        thread_id=thread_id,
        in_reply_to_message_id=in_reply_to_message_id,
        submission_id=submission_id,
    )

    return {
        "message_id": sent["message_id"],
        "sender_email": sender_email,
        "recipient_email": applicant_email,
        "loan_category": loan_category,
        "body": body,
    }


def build_decision_update_email_body(
    status: str, applicant_name: str, loan_category: str, bank_name: str, remarks: str | None = None
) -> str:
    prompt = DECISION_PROMPTS[status].format(
        applicant_name=applicant_name or "Applicant",
        loan_category=loan_category,
        bank_name=bank_name,
        remarks=remarks or "",
    )
    logger.info(
        "loan_apply agent: composing %s decision update with LLM (llama-3.3-70b-versatile) for bank %s...",
        status, bank_name,
    )
    response = llm.invoke(prompt)
    body = response.content if hasattr(response, "content") else str(response)
    body = body.strip()

    if status == "offer_more_documents" and remarks:
        # Appended verbatim rather than left to the LLM (see DECISION_PROMPTS'
        # instruction not to write this itself) — the bank's exact wording
        # (e.g. naming a specific document like "Employment Verification
        # Letter") must reach the applicant intact, never paraphrased,
        # summarized, or dropped by the model.
        body = f"{body}\n\nWhat {bank_name} needs from you:\n{remarks.strip()}\n\n{_REPLY_INSTRUCTION}"

    body = f"{body}\n\n{_SIGN_OFF}"
    logger.info("loan_apply agent: LLM composed %s decision update body (%d chars)", status, len(body))
    return body


def send_decision_update_email(
    status: str,
    applicant_name: str,
    applicant_email: str,
    loan_category: str,
    bank_name: str,
    thread_id: str | None,
    in_reply_to_message_id: str | None,
    remarks: str | None = None,
    submission_id: str | None = None,
) -> dict:
    """
    Composes (via LLM) and sends an email telling the applicant that
    bank_name has rejected / made an offer on / requested more documents for
    their application — threaded as a reply to the applicant's original
    message when a thread_id is available (it may not be, for submissions
    created before thread_id was captured).

    Called by celery_app.send_bank_decision_update_task once a bank records a
    decision via POST /bank-notifications/{id}/decision (see
    banks/notification_routes.py).
    """
    if status not in DECISION_PROMPTS:
        raise ValueError(f"Unknown decision status: {status!r}")

    body = build_decision_update_email_body(status, applicant_name, loan_category, bank_name, remarks)
    sender_email = _get_sender_email()
    subject = DECISION_SUBJECTS[status].format(loan_category=loan_category, bank_name=bank_name)
    if thread_id:
        subject = f"Re: {subject}"
    if submission_id:
        subject = application_id_tag(_get_or_create_short_code(submission_id), subject)
    logger.info(
        "loan_apply agent: sending %s decision update from %s to %s (bank=%s)",
        status, sender_email, applicant_email, bank_name,
    )

    sent = _send_email(
        sender_email, applicant_email,
        subject=subject,
        body=body,
        thread_id=thread_id,
        in_reply_to_message_id=in_reply_to_message_id,
        submission_id=submission_id,
    )

    return {
        "message_id": sent["message_id"],
        "sender_email": sender_email,
        "recipient_email": applicant_email,
        "loan_category": loan_category,
        "bank_name": bank_name,
        "status": status,
        "body": body,
    }
