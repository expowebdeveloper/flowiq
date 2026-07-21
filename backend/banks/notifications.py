import base64
import logging
from email.mime.text import MIMEText

from agent_activity import emit
from auth.oauth import build_gmail_service
from db import BankNotification, GmailToken, LoanApplyDocument, UserFormSubmission, get_session
from loan_recommendation.models import Bank, BankLoanPolicy

logger = logging.getLogger(__name__)


def _fallback_sender_email(session) -> str | None:
    token = session.query(GmailToken).first()
    return token.email if token else None


def _build_lead_email_body(submission: UserFormSubmission, documents: list[LoanApplyDocument]) -> str:
    lines = [
        f"A new {submission.loan_type.replace('_', ' ')} lead has completed document verification.",
        "",
        f"Applicant name: {submission.first_name} {submission.last_name}",
        f"Phone: {submission.phone_number or '-'}",
        f"Email: {submission.email}",
        f"Loan amount: {submission.loan_amount or '-'}",
        f"FICO score: {submission.fico_score or '-'}",
        f"ZIP code: {submission.zip_code}",
        "",
        "Documents submitted:",
    ]
    if documents:
        lines.extend(f"  - {doc.filename}" + (f" ({doc.label})" if doc.label else "") for doc in documents)
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def notify_banks_of_new_lead(submission_id: str) -> dict:
    """
    Emails every active bank with a loan policy for the lead's loan_type
    (via BankLoanPolicy/Bank — the admin-managed Banks table, same matching
    kyc.notify.notify_bank_of_kyc_completion uses) at its contact_email, and
    writes one BankNotification row per bank the email was actually
    delivered to, so each of those banks sees the lead the next time they
    check GET /bank-notifications. Idempotent per (submission, bank): safe
    to call more than once for the same submission (e.g. a lead that gets
    reprocessed) without creating duplicate rows or re-emailing a bank
    that's already been notified.

    Called once a lead's documents finish verifying — see
    loan_apply.document_processing.process_loan_applicant_reply, right after
    documents_status is set to "documents_complete".
    """
    session = get_session()
    try:
        submission = session.get(UserFormSubmission, submission_id)
        if not submission:
            return {"notified_count": 0, "skipped_banks": [], "reason": "Submission not found."}

        banks = (
            session.query(Bank)
            .join(BankLoanPolicy, BankLoanPolicy.bank_id == Bank.id)
            .filter(BankLoanPolicy.loan_type == submission.loan_type, Bank.status == "active")
            .distinct()
            .all()
        )
        if not banks:
            return {
                "notified_count": 0,
                "skipped_banks": [],
                "reason": f"No banks found offering '{submission.loan_type}'.",
            }

        existing_bank_names = {
            row.bank_name
            for row in session.query(BankNotification.bank_name).filter(
                BankNotification.submission_id == submission_id
            )
        }

        pending_banks = [bank for bank in banks if bank.name not in existing_bank_names]
        if not pending_banks:
            return {"notified_count": 0, "skipped_banks": [], "reason": None}

        sender_email = submission.mailbox_email or _fallback_sender_email(session)
        if not sender_email:
            reason = "No linked Gmail account found to send bank notifications from."
            logger.error("bank notifications: %s (submission %s)", reason, submission_id)
            emit("bank_notify", "error", reason, submission_id=submission_id)
            return {"notified_count": 0, "skipped_banks": [b.name for b in pending_banks], "reason": reason}

        documents = session.query(LoanApplyDocument).filter(
            LoanApplyDocument.submission_id == submission_id
        ).all()
        body = _build_lead_email_body(submission, documents)

        service = build_gmail_service(sender_email)

        notified_count = 0
        skipped_banks = []
        for bank in pending_banks:
            if not bank.contact_email:
                skipped_banks.append(bank.name)
                continue

            mime = MIMEText(body, "plain")
            mime["To"] = bank.contact_email
            mime["From"] = sender_email
            mime["Subject"] = (
                f"New {submission.loan_type.replace('_', ' ')} lead — "
                f"{submission.first_name} {submission.last_name}"
            )

            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
            try:
                service.users().messages().send(userId="me", body={"raw": raw}).execute()
            except Exception:
                logger.exception(
                    "bank notifications: failed to email %s for submission %s", bank.contact_email, submission_id
                )
                skipped_banks.append(bank.name)
                continue

            session.add(BankNotification(submission_id=submission_id, bank_name=bank.name))
            notified_count += 1

        session.commit()

        logger.info(
            "bank notifications: submission %s (%s) -> emailed %d bank(s), skipped %d of %d eligible: %s",
            submission_id, submission.loan_type, notified_count, len(skipped_banks), len(banks), skipped_banks,
        )
        if notified_count:
            emit(
                "bank_notify", "success",
                f"Notified {notified_count} bank(s) of new {submission.loan_type} lead",
                submission_id=submission_id,
                detail={"notified_count": notified_count, "skipped_banks": skipped_banks},
            )
        reason = None
        if skipped_banks:
            reason = f"No contact email (or send failed) for: {', '.join(skipped_banks)}."

        return {"notified_count": notified_count, "skipped_banks": skipped_banks, "reason": reason}
    except Exception as e:
        logger.exception("bank notifications: failed for submission %s", submission_id)
        emit("bank_notify", "error", f"Failed to notify banks: {e}", submission_id=submission_id)
        return {"notified_count": 0, "skipped_banks": [], "reason": f"Failed to notify banks: {e}"}
    finally:
        session.close()
