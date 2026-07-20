import os
import json
import secrets
import hashlib
import base64
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from db import get_session, GmailToken, OAuthVerifier, User
from auth.jwt import create_access_token, get_current_user

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("client_id")
GOOGLE_CLIENT_SECRET = os.getenv("client_secret")
REDIRECT_URI = "http://localhost:8000/auth/callback"

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError("client_id and client_secret must be set in .env")

# Build the client config dict that Flow accepts directly (no credentials.json needed)
CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uris": [REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

router = APIRouter(tags=["auth"])


@router.get("/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["sub"],
        "email": current_user["email"],
        "role": current_user["role"],
        "bank_name": current_user.get("bank_name"),
    }


def _pop_verifier(state: str) -> Optional[str]:
    session = get_session()
    try:
        row = session.get(OAuthVerifier, state)
        if not row:
            return None
        code_verifier = row.code_verifier
        session.delete(row)
        session.commit()
        return code_verifier
    finally:
        session.close()


def _save_verifier(state: str, code_verifier: str):
    session = get_session()
    try:
        session.merge(OAuthVerifier(state=state, code_verifier=code_verifier))
        session.commit()
    finally:
        session.close()


def get_credentials(email: str) -> Optional[Credentials]:
    session = get_session()
    try:
        row = session.get(GmailToken, email)
        if not row:
            return None
        creds = Credentials.from_authorized_user_info(json.loads(row.credentials_json), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            row.credentials_json = creds.to_json()
            session.commit()
        return creds if creds and creds.valid else None
    finally:
        session.close()


def save_credentials(email: str, creds: Credentials):
    session = get_session()
    try:
        session.merge(GmailToken(email=email, credentials_json=creds.to_json()))
        session.commit()
    finally:
        session.close()


def build_gmail_service(email: str):
    creds = get_credentials(email)
    if not creds:
        raise HTTPException(
            status_code=401,
            detail=f"Not authenticated. Visit /auth/link?email={email} to connect your Gmail."
        )
    return build("gmail", "v1", credentials=creds)


@router.get("/auth/link")
def link_email(email: Optional[str] = Query(None, description="Gmail address to pre-fill (optional)")):
    """Start the Google OAuth flow. If no email is given, Google's account chooser is shown."""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    state = secrets.token_urlsafe(24)
    _save_verifier(state, code_verifier)

    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    auth_kwargs = dict(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    if email:
        auth_kwargs["login_hint"] = email
    auth_url, _ = flow.authorization_url(**auth_kwargs)
    return RedirectResponse(auth_url)


@router.get("/auth/callback")
def auth_callback(code: str, state: str):
    """OAuth callback — saves token for the linked email."""
    try:
        code_verifier = _pop_verifier(state)

        flow = Flow.from_client_config(
            CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
            state=state,
        )
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
        flow.fetch_token(code=code, code_verifier=code_verifier)
        creds = flow.credentials

        user_info_service = build("oauth2", "v2", credentials=creds)
        user_info = user_info_service.userinfo().get().execute()
        actual_email = user_info.get("email", state)

        save_credentials(actual_email, creds)

        session = get_session()
        try:
            user = session.query(User).filter(User.email == actual_email).first()
            if not user:
                user = User(email=actual_email, password_hash="", role="broker")
                session.add(user)
                session.commit()
                session.refresh(user)
            token = create_access_token(user.id, user.email, user.role)
        finally:
            session.close()

        return RedirectResponse(f"http://localhost:5173/?linked=1&email={actual_email}&token={token}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")


@router.get("/auth/status")
def auth_status(email: str = Query(...)):
    """Check if an email is linked."""
    creds = get_credentials(email)
    return {"email": email, "linked": creds is not None}
