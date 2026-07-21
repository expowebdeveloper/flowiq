"""
Create (or update) a bank's contact_email / portal login fields on the
admin-managed `banks` table — a command-line equivalent of using the Banks
admin UI, for quickly configuring/testing the bank-notification email flow.
Works on both a brand-new bank name and one already created (via the UI or
an earlier run of this script).

Also keeps the bank-portal login (BankAccount, used to actually log in as
this bank and see its notifications/decisions) in sync with contact_email,
the same as the admin UI does — see bank_management.bank_login.sync_bank_login.
The first time a bank gets a contact_email, a login is created and its
generated password is printed here (it can't be recovered again afterwards).
To reset a lost password later, use scripts/create_bank_account.py with the
same --bank-name and --email.

Usage:
    python3 scripts/set_bank_contact.py --bank-name "Bank of America" --contact-email boa@example.com
    python3 scripts/set_bank_contact.py --bank-name "Jp Morgan" --contact-email jpm@example.com \\
        --portal-username jpm_agent --portal-password s3cret
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_session
from loan_recommendation.bank_management.bank_login import sync_bank_login
from loan_recommendation.models import Bank


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bank-name", required=True, help='e.g. "Bank of America"')
    parser.add_argument("--contact-email", help="Where bank-syncing emails get sent, and the bank's FlowIQ login")
    parser.add_argument("--portal-username", help="Login for the bank's own external portal")
    parser.add_argument("--portal-password", help="Login for the bank's own external portal")
    args = parser.parse_args()

    session = get_session()
    try:
        bank = session.query(Bank).filter(Bank.name == args.bank_name).first()
        old_name = bank.name if bank else None

        if bank:
            action = "Updated"
        else:
            action = "Created"
            bank = Bank(name=args.bank_name)
            session.add(bank)

        if args.contact_email is not None:
            bank.contact_email = args.contact_email
        if args.portal_username is not None:
            bank.portal_username = args.portal_username
        if args.portal_password is not None:
            bank.portal_password = args.portal_password

        session.commit()
        session.refresh(bank)

        login_password = sync_bank_login(session, bank, old_name=old_name)

        print(f"{action} bank:")
        print(f"  Name            : {bank.name}")
        print(f"  Contact email   : {bank.contact_email or '-'}")
        print(f"  Portal username : {bank.portal_username or '-'}")
        print(f"  Portal password : {'(set)' if bank.portal_password else '-'}")
        if login_password:
            print("\nFlowIQ login created for this bank (share securely):")
            print(f"  Email    : {bank.contact_email}")
            print(f"  Password : {login_password}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
