from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from auth.jwt import create_access_token, verify_password
from db import BankAccount, User, get_session

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    email: str
    role: str
    bank_name: str | None = None


@router.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """Email+password login. Currently used by bank accounts; brokers/users sign in via Google."""
    session = get_session()
    try:
        bank = session.query(BankAccount).filter(BankAccount.email == req.email).first()
        if bank and verify_password(req.password, bank.password_hash):
            token = create_access_token(bank.id, bank.email, "bank", bank_name=bank.bank_name)
            return LoginResponse(token=token, email=bank.email, role="bank", bank_name=bank.bank_name)

        user = session.query(User).filter(User.email == req.email).first()
        if user and user.password_hash and verify_password(req.password, user.password_hash):
            token = create_access_token(user.id, user.email, user.role)
            return LoginResponse(token=token, email=user.email, role=user.role)

        raise HTTPException(status_code=401, detail="Invalid email or password")
    finally:
        session.close()
