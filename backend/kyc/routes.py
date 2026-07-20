import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from agents.documents import (
    extract_pdf_text,
    extract_image_text,
    looks_like_aadhaar,
    DOCUMENT_VALIDATORS,
    IMAGE_MIME_TYPES,
    IMAGE_EXTENSIONS,
)
from banks.constants import LOAN_TYPES, MAX_DOCUMENTS, MAX_DOCUMENT_SIZE
from db import BankLoanRate, LoanApplication, LoanApplicationDocument, get_session
from kyc.notify import notify_bank_of_kyc_completion

router = APIRouter(prefix="/kyc", tags=["kyc"])

APPLICATIONS_DIR = Path("applications")
APPLICATIONS_DIR.mkdir(exist_ok=True)


def _get_application_by_token(session, token: str) -> LoanApplication:
    application = session.query(LoanApplication).filter(LoanApplication.kyc_token == token).first()
    if not application:
        raise HTTPException(status_code=404, detail="This KYC link is invalid or has already been used.")
    return application


@router.get("/{token}")
def get_kyc_application(token: str):
    """Public: fetch prefill data + required documents for a KYC link."""
    session = get_session()
    try:
        application = _get_application_by_token(session, token)

        bank_rate = None
        if application.bank_loan_rate_id:
            bank_rate = session.get(BankLoanRate, application.bank_loan_rate_id)

        return {
            "bank_name": application.bank_name,
            "loan_type": application.loan_type,
            "loan_types": LOAN_TYPES,
            "applicant_name": application.applicant_name,
            "applicant_phone": application.applicant_phone,
            "applicant_email": application.applicant_email,
            "date_of_birth": application.date_of_birth,
            "gender": application.gender,
            "address": application.address,
            "required_documents": bank_rate.required_documents if bank_rate else None,
        }
    finally:
        session.close()


@router.post("/{token}")
async def submit_kyc_application(
    token: str,
    applicant_name: str = Form(...),
    applicant_phone: str = Form(...),
    applicant_email: Optional[str] = Form(None),
    credit_score: Optional[str] = Form(None),
    loan_type: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    documents: list[UploadFile] = File(default=[]),
    document_labels: Optional[str] = Form(None),
):
    """Public: applicant completes their KYC — personal details, credit score, documents."""
    if len(documents) > MAX_DOCUMENTS:
        raise HTTPException(status_code=400, detail=f"Too many documents (max {MAX_DOCUMENTS})")

    labels: list[Optional[str]] = []
    if document_labels:
        try:
            labels = json.loads(document_labels)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="document_labels must be a JSON array")
        if not isinstance(labels, list):
            raise HTTPException(status_code=400, detail="document_labels must be a JSON array")

    if loan_type and loan_type not in LOAN_TYPES:
        raise HTTPException(status_code=400, detail=f"loan_type must be one of {LOAN_TYPES}")

    session = get_session()
    try:
        application = _get_application_by_token(session, token)

        application.applicant_name = applicant_name
        application.applicant_phone = applicant_phone
        application.applicant_email = applicant_email
        application.credit_score = credit_score
        application.date_of_birth = date_of_birth
        application.gender = gender
        application.address = address
        if loan_type:
            application.loan_type = loan_type
        application.status = "kyc_completed"
        application.kyc_submitted_at = datetime.now(timezone.utc)
        application.kyc_token = None  # invalidate the link so it can't be resubmitted
        session.add(application)
        session.commit()
        session.refresh(application)

        app_dir = APPLICATIONS_DIR / application.id
        app_dir.mkdir(exist_ok=True)

        aadhaar_verified = False
        for index, upload in enumerate(documents):
            if not upload.filename:
                continue
            data = await upload.read()
            if len(data) > MAX_DOCUMENT_SIZE:
                raise HTTPException(status_code=400, detail=f"'{upload.filename}' exceeds max size of 15MB")

            label = labels[index] if index < len(labels) else None
            doc = LoanApplicationDocument(
                application_id=application.id,
                filename=upload.filename,
                saved_path="",
                content_type=upload.content_type,
                label=label,
            )
            session.add(doc)
            session.flush()

            safe_name = f"{doc.id}_{upload.filename}"
            file_path = app_dir / safe_name
            file_path.write_bytes(data)
            doc.saved_path = str(file_path)

            mime = upload.content_type or ""
            is_pdf = mime == "application/pdf" or upload.filename.lower().endswith(".pdf")
            is_image = mime in IMAGE_MIME_TYPES or upload.filename.lower().endswith(IMAGE_EXTENSIONS)

            text = ""
            if is_pdf:
                text = extract_pdf_text(data)
            elif is_image:
                text = extract_image_text(data)

            if not aadhaar_verified and text and looks_like_aadhaar(upload.filename, text):
                aadhaar_verified = True

            validator_entry = DOCUMENT_VALIDATORS.get((label or "").strip().lower())
            if validator_entry:
                kind, validator = validator_entry
                if kind == "image" and is_image:
                    doc.content_verified = validator(data)
                elif kind == "text" and text:
                    doc.content_verified = validator(text)
                else:
                    doc.content_verified = False

        application.aadhaar_verified = aadhaar_verified
        session.commit()
        application_id = application.id
    finally:
        session.close()

    notify_result = notify_bank_of_kyc_completion(application_id)

    return {
        "status": "kyc_completed",
        "message": "Your KYC has been submitted successfully.",
        "bank_notified": notify_result["sent"],
        "banks_notified_count": notify_result["notified_count"],
        "bank_notification_warning": notify_result["reason"],
    }
