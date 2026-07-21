"""
One-off backfill script: re-runs bank syncing for every lead whose documents
were already marked complete before banks/notifications.py was switched from
the legacy BankAccount/bank_loan_rates lookup to the admin-managed
banks/bank_loan_policies tables. This actually emails each eligible bank's
contact_email (via the lead's linked Gmail mailbox) and only records a
BankNotification row once that email sends successfully.
notify_banks_of_new_lead is idempotent per (submission, bank) — it skips
banks already notified — so this is safe to run more than once without
duplicate emails.

Usage: python3 scripts/resync_leads_to_banks.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from banks.notifications import notify_banks_of_new_lead
from db import UserFormSubmission, get_session


def main():
    session = get_session()
    try:
        submission_ids = [
            row.id
            for row in session.query(UserFormSubmission.id)
            .filter(UserFormSubmission.documents_status == "documents_complete")
            .all()
        ]
    finally:
        session.close()

    print(f"Found {len(submission_ids)} lead(s) with completed documents.\n")

    total_notified = 0
    for submission_id in submission_ids:
        result = notify_banks_of_new_lead(submission_id)
        notified = result.get("notified_count", 0)
        total_notified += notified
        status = f"notified {notified} bank(s)" if notified else (result.get("reason") or "no new banks")
        print(f"{submission_id}: {status}")

    print(f"\nDone. {total_notified} new bank notification(s) created across {len(submission_ids)} lead(s).")


if __name__ == "__main__":
    main()
