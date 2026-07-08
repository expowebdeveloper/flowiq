import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from auth import require_broker
from db import BankLoanRate, LoanApplication, LoanApplicationDocument, get_session

router = APIRouter(prefix="/loan-applications", tags=["loan-applications"])

APPLICATIONS_DIR = Path("applications")
APPLICATIONS_DIR.mkdir(exist_ok=True)

MAX_DOCUMENTS = 20
MAX_DOCUMENT_SIZE = 15 * 1024 * 1024  # 15 MB per file


def _serialize(app: LoanApplication, documents: list[LoanApplicationDocument]) -> dict:
    return {
        "id": app.id,
        "bank_loan_rate_id": app.bank_loan_rate_id,
        "bank_name": app.bank_name,
        "loan_type": app.loan_type,
        "applicant_name": app.applicant_name,
        "applicant_phone": app.applicant_phone,
        "applicant_email": app.applicant_email,
        "notes": app.notes,
        "status": app.status,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "documents": [
            {"id": d.id, "filename": d.filename, "content_type": d.content_type, "label": d.label,
             "download_url": f"/loan-applications/{app.id}/documents/{d.id}"}
            for d in documents
        ],
    }


@router.post("")
async def submit_loan_application(
    bank_loan_rate_id: str = Form(...),
    applicant_name: str = Form(...),
    applicant_phone: str = Form(...),
    applicant_email: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    documents: list[UploadFile] = File(default=[]),
    document_labels: Optional[str] = Form(None),
    current_user: dict = Depends(require_broker),
):
    """Broker submits a loan application for a specific bank + loan type, with supporting documents.

    document_labels is a JSON array of strings, parallel to documents, naming which
    required document (e.g. "PAN card") each uploaded file satisfies.
    """
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

    session = get_session()
    try:
        bank_rate = session.get(BankLoanRate, bank_loan_rate_id)
        if not bank_rate:
            raise HTTPException(status_code=404, detail="Bank loan rate not found")

        application = LoanApplication(
            broker_id=current_user["sub"],
            bank_loan_rate_id=bank_rate.id,
            bank_name=bank_rate.bank_name,
            loan_type=bank_rate.loan_type,
            applicant_name=applicant_name,
            applicant_phone=applicant_phone,
            applicant_email=applicant_email,
            notes=notes,
        )
        session.add(application)
        session.commit()
        session.refresh(application)

        app_dir = APPLICATIONS_DIR / application.id
        app_dir.mkdir(exist_ok=True)

        saved_documents = []
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
            saved_documents.append(doc)

        session.commit()
        for d in saved_documents:
            session.refresh(d)

        return _serialize(application, saved_documents)
    finally:
        session.close()


@router.get("")
def list_loan_applications(current_user: dict = Depends(require_broker)):
    """List loan applications submitted by the current broker."""
    session = get_session()
    try:
        apps = session.query(LoanApplication).filter(
            LoanApplication.broker_id == current_user["sub"]
        ).order_by(LoanApplication.created_at.desc()).all()

        result = []
        for app in apps:
            docs = session.query(LoanApplicationDocument).filter(
                LoanApplicationDocument.application_id == app.id
            ).all()
            result.append(_serialize(app, docs))
        return {"count": len(result), "applications": result}
    finally:
        session.close()


@router.get("/{application_id}/documents/{document_id}")
def download_application_document(application_id: str, document_id: str, current_user: dict = Depends(require_broker)):
    """Download a document attached to one of the current broker's loan applications."""
    session = get_session()
    try:
        app = session.get(LoanApplication, application_id)
        if not app or app.broker_id != current_user["sub"]:
            raise HTTPException(status_code=404, detail="Application not found")

        doc = session.get(LoanApplicationDocument, document_id)
        if not doc or doc.application_id != application_id:
            raise HTTPException(status_code=404, detail="Document not found")

        file_path = Path(doc.saved_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        from fastapi.responses import FileResponse
        return FileResponse(str(file_path), filename=doc.filename)
    finally:
        session.close()
