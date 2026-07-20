import logging

from agent_activity import emit
from db import BankAccount, BankLoanRate, BankNotification, UserFormSubmission, get_session

logger = logging.getLogger(__name__)


def notify_banks_of_new_lead(submission_id: str) -> dict:
    """
    Writes one BankNotification row per bank that offers the lead's
    loan_type (via BankLoanRate — same matching kyc.notify.notify_bank_of_kyc_completion
    uses for its email notification), so each of those banks sees the lead
    the next time they check GET /bank-notifications. Idempotent per
    (submission, bank): safe to call more than once for the same submission
    (e.g. a lead that gets reprocessed) without creating duplicate rows.

    Called once a lead's documents finish verifying — see
    loan_apply.document_processing.process_loan_applicant_reply, right after
    documents_status is set to "documents_complete".
    """
    session = get_session()
    try:
        submission = session.get(UserFormSubmission, submission_id)
        if not submission:
            return {"notified_count": 0, "skipped_banks": [], "reason": "Submission not found."}

        bank_names = [
            row.bank_name
            for row in session.query(BankLoanRate.bank_name)
            .filter(BankLoanRate.loan_type == submission.loan_type)
            .distinct()
        ]
        if not bank_names:
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

        notified_count = 0
        skipped_banks = []
        for bank_name in bank_names:
            if bank_name in existing_bank_names:
                continue  # already notified this bank about this lead

            bank_account = session.query(BankAccount).filter(BankAccount.bank_name == bank_name).first()
            if not bank_account:
                skipped_banks.append(bank_name)
                continue

            session.add(BankNotification(submission_id=submission_id, bank_name=bank_name))
            notified_count += 1

        session.commit()

        logger.info(
            "bank notifications: submission %s (%s) -> notified %d bank(s), skipped %d (no account): %s",
            submission_id, submission.loan_type, notified_count, len(skipped_banks), skipped_banks,
        )
        if notified_count:
            emit(
                "bank_notify", "success",
                f"Notified {notified_count} bank(s) of new {submission.loan_type} lead",
                submission_id=submission_id,
                detail={"notified_count": notified_count, "skipped_banks": skipped_banks},
            )

        return {"notified_count": notified_count, "skipped_banks": skipped_banks, "reason": None}
    except Exception as e:
        logger.exception("bank notifications: failed for submission %s", submission_id)
        emit("bank_notify", "error", f"Failed to notify banks: {e}", submission_id=submission_id)
        return {"notified_count": 0, "skipped_banks": [], "reason": f"Failed to notify banks: {e}"}
    finally:
        session.close()
