"""
One-off backfill: provisions a FlowIQ login (BankAccount) for every bank in
the admin-managed `banks` table that already has a contact_email but was
created/edited before bank_management.bank_login.sync_bank_login existed —
so banks created via the UI or scripts/set_bank_contact.py before this
feature landed still get a login, exactly as if you'd just re-saved them.

Safe to run more than once: sync_bank_login only creates a login the first
time (matched by bank_name or contact_email); if one already exists it just
keeps bank_name/email in sync and never touches the password again.

No lead/notification data needs migrating separately — BankNotification/
BankDecision rows are matched to a login purely by the bank_name string at
request time, so every existing notification for a bank becomes visible as
soon as that bank has a login with a matching bank_name.

Usage: python3 scripts/migrate_bank_logins.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_session
from loan_recommendation.bank_management.bank_login import sync_bank_login
from loan_recommendation.models import Bank


def main():
    session = get_session()
    try:
        banks = session.query(Bank).filter(Bank.contact_email.isnot(None)).all()
        print(f"Found {len(banks)} bank(s) with a contact_email.\n")

        created = []
        for bank in banks:
            password = sync_bank_login(session, bank)
            if password:
                created.append((bank.name, bank.contact_email, password))
                print(f"{bank.name}: login created")
            else:
                print(f"{bank.name}: already has a login (or none needed)")

        if created:
            print("\nNew logins (share these with each bank securely — passwords can't be shown again):")
            print(f"{'Bank':<25} {'Email':<30} {'Password'}")
            for name, email, password in created:
                print(f"{name:<25} {email:<30} {password}")
        else:
            print("\nNo new logins were needed.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
