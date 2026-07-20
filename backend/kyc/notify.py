import base64
from email.mime.text import MIMEText

from auth.oauth import build_gmail_service
from db import BankAccount, BankLoanRate, LoanApplication, LoanApplicationDocument, User, get_session


def notify_bank_of_kyc_completion(application_id: str) -> dict:
    """
    Emails every bank that offers the applicant's loan_type (via BankLoanRate)
    a summary of a completed KYC application, sent from the broker's linked
    Gmail account. Returns a dict describing how many banks were notified vs.
    skipped (no registered contact email), so the caller can surface a warning
    without failing the KYC submission itself.
    """
    session = get_session()
    try:
        application = session.get(LoanApplication, application_id)
        if not application:
            return {"sent": False, "notified_count": 0, "skipped_banks": [], "reason": "Application not found."}

        broker = session.get(User, application.broker_id)
        if not broker:
            return {"sent": False, "notified_count": 0, "skipped_banks": [], "reason": "Broker account not found."}

        bank_names = [
            row.bank_name
            for row in session.query(BankLoanRate.bank_name)
            .filter(BankLoanRate.loan_type == application.loan_type)
            .distinct()
        ]
        if not bank_names:
            return {
                "sent": False,
                "notified_count": 0,
                "skipped_banks": [],
                "reason": f"No banks found offering '{application.loan_type}'.",
            }

        documents = session.query(LoanApplicationDocument).filter(
            LoanApplicationDocument.application_id == application.id
        ).all()

        body_lines = [
            f"A new KYC application has been completed for {application.loan_type.replace('_', ' ')}.",
            "",
            f"Applicant name: {application.applicant_name}",
            f"Phone: {application.applicant_phone}",
            f"Email: {application.applicant_email or '-'}",
            f"Date of birth: {application.date_of_birth or '-'}",
            f"Gender: {application.gender or '-'}",
            f"Address: {application.address or '-'}",
            f"Credit score (self-reported): {application.credit_score or '-'}",
            f"Loan type: {application.loan_type}",
            "",
            "Documents submitted:",
        ]
        if documents:
            body_lines.extend(f"  - {doc.filename}" + (f" ({doc.label})" if doc.label else "") for doc in documents)
        else:
            body_lines.append("  (none)")
        body = "\n".join(body_lines)

        service = build_gmail_service(broker.email)

        notified_count = 0
        skipped_banks = []
        for bank_name in bank_names:
            bank_account = session.query(BankAccount).filter(BankAccount.bank_name == bank_name).first()
            if not bank_account:
                skipped_banks.append(bank_name)
                continue

            mime = MIMEText(body, "plain")
            mime["To"] = bank_account.email
            mime["From"] = broker.email
            mime["Subject"] = f"KYC completed — {application.applicant_name} ({application.loan_type})"

            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
            try:
                service.users().messages().send(userId="me", body={"raw": raw}).execute()
                notified_count += 1
            except Exception:
                skipped_banks.append(bank_name)

        reason = None
        if skipped_banks:
            reason = f"No registered contact email (or send failed) for: {', '.join(skipped_banks)}."

        return {
            "sent": notified_count > 0,
            "notified_count": notified_count,
            "skipped_banks": skipped_banks,
            "reason": reason,
        }
    except Exception as e:
        return {"sent": False, "notified_count": 0, "skipped_banks": [], "reason": f"Failed to send notifications: {e}"}
    finally:
        session.close()
