"""
One-off seed script: creates a BankAccount login (email + password) for each
real bank currently present in bank_loan_rates, so each bank can sign in and
view loan applications submitted to it.

Usage: python3 scripts/seed_bank_accounts.py
"""
import secrets
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.jwt import hash_password
from db import BankAccount, BankLoanRate, get_session

BANK_EMAIL_SLUGS = {
    "Bank of America": "bofa",
    "JPMorgan Chase Bank": "chase",
    "Wells Fargo Bank": "wellsfargo",
}


def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main():
    session = get_session()
    try:
        real_bank_names = {
            row.bank_name for row in session.query(BankLoanRate.bank_name).distinct()
            if row.bank_name in BANK_EMAIL_SLUGS
        }

        created = []
        for bank_name in sorted(real_bank_names):
            existing = session.query(BankAccount).filter(BankAccount.bank_name == bank_name).first()
            if existing:
                print(f"SKIP  {bank_name}: already has a login ({existing.email})")
                continue

            slug = BANK_EMAIL_SLUGS[bank_name]
            email = f"{slug}@flowiq.bank"
            password = generate_password()

            account = BankAccount(
                bank_name=bank_name,
                email=email,
                password_hash=hash_password(password),
            )
            session.add(account)
            created.append((bank_name, email, password))

        session.commit()

        if created:
            print("\nCreated bank logins (share these with each bank contact securely):")
            print(f"{'Bank':<25} {'Email':<25} {'Password'}")
            for bank_name, email, password in created:
                print(f"{bank_name:<25} {email:<25} {password}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
