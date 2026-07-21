"""
Create (or reset the password of) a single bank login — connects using the
same DATABASE_URL that db.py already loads from backend/.env, so it always
targets whatever Postgres the app itself is pointed at.

Usage:
    python3 scripts/create_bank_account.py --bank-name "HDFC Bank" --email hdfc@flowiq.bank
    python3 scripts/create_bank_account.py --bank-name "HDFC Bank" --email hdfc@flowiq.bank --password mypassword

If --password is omitted, a random one is generated and printed. If a login
already exists for that bank_name or email, its password is reset instead of
failing (useful for resetting a forgotten password during local testing).
"""
import argparse
import secrets
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.jwt import hash_password
from db import BankAccount, get_session


def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bank-name", required=True, help='e.g. "HDFC Bank"')
    parser.add_argument("--email", required=True, help="Login email, e.g. hdfc@flowiq.bank")
    parser.add_argument("--password", help="If omitted, a random password is generated")
    args = parser.parse_args()

    password = args.password or generate_password()

    session = get_session()
    try:
        existing = (
            session.query(BankAccount)
            .filter((BankAccount.bank_name == args.bank_name) | (BankAccount.email == args.email))
            .first()
        )

        if existing:
            action = "Password reset"
            existing.bank_name = args.bank_name
            existing.email = args.email
            existing.password_hash = hash_password(password)
        else:
            action = "Created"
            session.add(
                BankAccount(
                    bank_name=args.bank_name,
                    email=args.email,
                    password_hash=hash_password(password),
                )
            )

        session.commit()

        print(f"{action} bank login:")
        print(f"  Bank name : {args.bank_name}")
        print(f"  Email     : {args.email}")
        print(f"  Password  : {password}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
