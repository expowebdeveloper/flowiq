import secrets
import string

from sqlalchemy.orm import Session

from auth.jwt import hash_password
from db import BankAccount
from loan_recommendation.models import Bank


def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def sync_bank_login(db: Session, bank: Bank, old_name: str | None = None) -> str | None:
    """
    Keeps the bank-portal login (BankAccount, matched to Bank purely by an
    identical bank_name string — see db.BankNotification/BankDecision) in
    sync with the admin-managed Bank row, so creating or editing a bank in
    the Banks UI is enough to log in as it — no separate
    scripts/create_bank_account.py run required.

    - No contact_email on the bank: nothing to do, there's no email to log
      in with.
    - An existing login is found (by old_name, pre-rename, or by
      contact_email): its bank_name/email are updated to match; its
      password is left untouched.
    - No existing login: one is created with a freshly generated password,
      which is returned so the caller can surface it to the admin exactly
      once (it can never be recovered again — only reset).

    old_name should be the bank's name *before* this save (pass it when
    updating an existing bank, omit/None when creating), so a rename still
    finds the account it needs to follow.
    """
    if not bank.contact_email:
        return None

    account = (
        db.query(BankAccount)
        .filter(BankAccount.bank_name == (old_name or bank.name))
        .first()
    )
    if not account:
        account = db.query(BankAccount).filter(BankAccount.email == bank.contact_email).first()

    if account:
        account.bank_name = bank.name
        account.email = bank.contact_email
        db.commit()
        return None

    password = _generate_password()
    db.add(BankAccount(bank_name=bank.name, email=bank.contact_email, password_hash=hash_password(password)))
    db.commit()
    return password
