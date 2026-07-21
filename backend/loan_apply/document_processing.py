import json
import logging
from datetime import datetime, timezone

import re

from agent_activity import emit
from agents.documents import (
    DOCUMENT_VALIDATORS,
    IMAGE_EXTENSIONS,
    IMAGE_MIME_TYPES,
    extract_image_text_candidates,
    extract_pdf_text,
)
from auth.oauth import build_gmail_service
from banks.constants import MAX_DOCUMENT_SIZE
from banks.notifications import notify_banks_of_new_lead
from db import LoanApplyDocument, UserFormSubmission, get_session
from inbound.extraction import extract_parts
from .agent import (
    send_annual_income_mismatch_email,
    send_documents_complete_email,
    send_missing_documents_email,
)
from .field_extraction import extract_fields_from_text
from .requirements import get_required_documents

logger = logging.getLogger(__name__)


def _normalize(s: str) -> str:
    """Collapses '_'/'-'/multiple spaces to single spaces so 'aadhaar_card.png'
    and 'Aadhaar Card' compare equal — filenames rarely match a document's
    display name verbatim, but do carry the same words."""
    return re.sub(r"[\s_\-]+", " ", s).strip().lower()


def _singularize(s: str) -> str:
    """Strips a trailing plural 's' off the last word only (e.g. 'bank
    statements' -> 'bank statement'), so a filename like 'bank_statement.png'
    still matches a required document named in the plural. Deliberately
    narrow — only the final word, only a bare trailing 's' — since this is a
    substring-match fallback, not general stemming, and a broader rule risks
    collapsing unrelated document names into each other."""
    return re.sub(r"s\b", "", s.strip(), count=1) if s.endswith("s") else s


def _normalize_money(value: str) -> str:
    """
    Normalizes a money string for an EXACT-match comparison — strips
    currency symbols/commas/whitespace and trailing ".00"-style zero
    decimals, so "$200,000.00" (OCR'd from a document) and "200000" (typed
    into the applicant form) compare equal despite differing only in
    formatting, while any actual figure difference still fails the match.
    """
    cleaned = re.sub(r"[^\d.]", "", value or "")
    if not cleaned:
        return ""
    if "." in cleaned:
        cleaned = cleaned.rstrip("0").rstrip(".")
    return cleaned


def _match_document_label(filename: str, text: str, required_doc_names: list[str]) -> str | None:
    """
    Matches an attachment to one of the loan's required document names.
    Any required document with a registered content validator (see
    agents.documents.DOCUMENT_VALIDATORS) is matched by content, independent
    of filename — OCR text rarely repeats a document's exact display name.
    Only documents with no registered validator fall back to a normalized
    substring match between the required name and the filename/text.
    """
    for name in required_doc_names:
        validator_entry = DOCUMENT_VALIDATORS.get(name.strip().lower())
        if validator_entry:
            kind, validator = validator_entry
            if kind == "text" and text and validator(text):
                return name

    haystack = _normalize(f"{filename} {text}")
    for name in required_doc_names:
        normalized_name = _normalize(name)
        if normalized_name in haystack or _singularize(normalized_name) in haystack:
            return name
    return None


def find_missing_documents(session, submission_id: str, required_docs: list[dict]) -> list[dict]:
    """
    Compares the full required-documents list against every LoanApplyDocument
    ever received for this submission (across all of the applicant's replies,
    not just the latest one). A required document only counts as satisfied if
    some received attachment was matched to it AND passed content validation
    (content_verified is True) — an unreadable/wrong attachment counts the same
    as not having sent it at all.

    Not underscore-prefixed — also called from
    celery_app.send_missing_document_reminders to recompute a lead's still-
    missing documents outside the reply-processing flow.
    """
    received = (
        session.query(LoanApplyDocument)
        .filter(LoanApplyDocument.submission_id == submission_id)
        .all()
    )
    verified_labels = {d.label for d in received if d.label and d.content_verified is True}
    return [doc for doc in required_docs if doc["document"] not in verified_labels]


def process_loan_applicant_reply(mailbox_email: str, sender_email: str, message_id: str, submission_id: str) -> dict:
    """
    Given a reply from a known loan applicant containing document attachments,
    extracts text from each attachment, validates it against the required
    documents for their loan type, pulls out structured field values (gold
    weight, property value, etc.), and updates that applicant's
    UserFormSubmission row accordingly.

    mailbox_email is the linked broker Gmail account the message was fetched
    from (we only have OAuth access to that mailbox, never the applicant's own
    inbox); sender_email is the applicant's address the message arrived FROM.
    submission_id is resolved by the caller from the message's [application id: ...]
    tag (see loan_apply.agent.extract_application_id and
    celery_app.poll_loan_applicant_replies) — passed explicitly rather than
    re-derived here from sender_email alone, since one applicant email address
    can have more than one submission.
    """
    session = get_session()
    try:
        submission = session.get(UserFormSubmission, submission_id)
        if not submission or submission.email != sender_email:
            return {
                "status": "skipped",
                "reason": f"No loan_apply submission {submission_id} found for {sender_email}",
            }

        loan_type = submission.loan_type
        applicant_display_name = f"{submission.first_name} {submission.last_name}"
        existing_extracted = json.loads(submission.extracted_data) if submission.extracted_data else {}
        extra_loan_details = json.loads(submission.extra_loan_details) if submission.extra_loan_details else {}
        declared_annual_income = extra_loan_details.get("annual_income")
    finally:
        session.close()

    emit(
        "document_processing", "started",
        f"Processing documents from {applicant_display_name} ({sender_email})",
        submission_id=submission_id,
    )

    info = get_required_documents(loan_type)
    required_doc_names = [d["document"] for d in info["general_documents"] + info["category_documents"]]

    service = build_gmail_service(mailbox_email)

    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = msg.get("payload", {})
    parts = payload.get("parts", [])
    if not parts:
        return {"status": "skipped", "reason": "Message has no attachments"}

    extracted = extract_parts(parts, service, "me", message_id, sender_email)
    attachments = extracted["attachments"]
    if not attachments:
        return {"status": "skipped", "reason": "Message has no attachments"}

    merged_fields = dict(existing_extracted)
    processed_docs = []
    # Set when this reply's "Annual Income" document is structurally a valid
    # income certification (passed validate_annual_income_certificate) but its
    # OCR'd certified figure doesn't exactly match what the applicant declared
    # in extra_loan_details.annual_income at submission time — distinct from
    # "missing" (no such document was sent at all), since here one WAS sent,
    # it just doesn't corroborate the declared figure. Drives a dedicated
    # mismatch email (see send_annual_income_mismatch_email below) instead of
    # the generic "still missing" one, and forces content_verified=False so
    # find_missing_documents keeps blocking completion/bank notification the
    # same way an actually-missing document would.
    annual_income_mismatch: dict | None = None

    session = get_session()
    try:
        for attachment in attachments:
            filename = attachment["filename"]
            saved_path = attachment["saved_path"]
            mime = attachment.get("mime_type", "")

            with open(saved_path, "rb") as f:
                data = f.read()
            if len(data) > MAX_DOCUMENT_SIZE:
                logger.warning("loan_apply documents: skipping oversized attachment %s", filename)
                continue

            is_pdf = mime == "application/pdf" or filename.lower().endswith(".pdf")
            is_image = mime in IMAGE_MIME_TYPES or filename.lower().endswith(IMAGE_EXTENSIONS)

            text = ""
            ocr_candidates: list[str] = []
            if is_pdf:
                text = extract_pdf_text(data)
            elif is_image:
                ocr_candidates = extract_image_text_candidates(data)
                text = max(ocr_candidates, key=len, default="")

            label = _match_document_label(filename, text, required_doc_names)

            content_verified = None
            validator_entry = DOCUMENT_VALIDATORS.get((label or "").strip().lower())
            if validator_entry:
                kind, validator = validator_entry
                if kind == "image" and is_image:
                    content_verified = validator(data)
                elif kind == "text" and text:
                    content_verified = validator(text)
                else:
                    content_verified = False

            extracted_this_doc = {}
            if text:
                extracted_this_doc = extract_fields_from_text(info["category"], text, label, ocr_candidates)
                merged_fields.update(extracted_this_doc)

            # Cross-check only fires once the document has already passed its
            # own structural validator — an unreadable/wrong document is
            # already handled by the existing content_verified=False path
            # above and counted in unclear_count below, so this is strictly
            # for "looks like a real income certificate, but the number is
            # wrong" rather than duplicating that handling.
            if (
                label == "Annual Income"
                and content_verified
                and declared_annual_income not in (None, "")
                and "certified_annual_income" in extracted_this_doc
            ):
                certified_value = extracted_this_doc["certified_annual_income"]
                if _normalize_money(certified_value) != _normalize_money(str(declared_annual_income)):
                    content_verified = False
                    annual_income_mismatch = {
                        "filename": filename,
                        "declared": declared_annual_income,
                        "certified": certified_value,
                    }

            doc = LoanApplyDocument(
                submission_id=submission_id,
                message_id=message_id,
                filename=filename,
                saved_path=saved_path,
                content_type=mime,
                label=label,
                content_verified=content_verified,
            )
            session.add(doc)
            processed_docs.append({"filename": filename, "label": label, "content_verified": content_verified})

        session.flush()  # so _find_missing_documents' query sees the docs just added above
        required_docs = info["general_documents"] + info["category_documents"]
        missing_docs = find_missing_documents(session, submission_id, required_docs)
        # Attachments sent THIS reply that didn't match any required document at
        # all — i.e. the applicant did send something, we just couldn't tell what
        # it was (blurry/low-res/wrong crop/etc.), as opposed to not sending it.
        # A mismatched Annual Income document DID match a required document (it's
        # excluded here so it isn't double-counted as "unclear" too).
        unclear_count = sum(
            1 for d in processed_docs
            if d["label"] is None and not (annual_income_mismatch and d["filename"] == annual_income_mismatch["filename"])
        )

        submission = session.get(UserFormSubmission, submission_id)
        submission.extracted_data = json.dumps(merged_fields)
        submission.documents_status = "documents_incomplete" if missing_docs else "documents_complete"
        submission.documents_processed_at = datetime.now(timezone.utc)
        # Any reply — even one that leaves documents still incomplete — is
        # fresh applicant engagement, so it earns a fresh 3-reminder
        # allowance rather than picking up where a stale count left off. See
        # celery_app.send_missing_document_reminders for where this is spent.
        submission.reminder_count = 0
        submission.last_reminder_sent_at = None
        applicant_name = f"{submission.first_name} {submission.last_name}"
        loan_category = info["category"]
        session.commit()
    finally:
        session.close()

    logger.info(
        "loan_apply documents: processed %d attachment(s) for submission %s (%s), %d document(s) still "
        "missing/unverified, %d unclear this reply, extracted_data=%s",
        len(processed_docs), submission_id, sender_email, len(missing_docs), unclear_count, merged_fields,
    )
    emit(
        "document_processing",
        "success" if not (missing_docs or unclear_count or annual_income_mismatch) else "info",
        f"Verified {len(processed_docs) - unclear_count}/{len(processed_docs)} document(s) from "
        f"{applicant_name} — {len(missing_docs)} still missing/unverified"
        + (f", {unclear_count} unclear" if unclear_count else "")
        + (
            f", Annual Income mismatch (declared {annual_income_mismatch['declared']}, "
            f"certified {annual_income_mismatch['certified']})"
            if annual_income_mismatch else ""
        ),
        submission_id=submission_id,
        detail={
            "documents": processed_docs,
            "missing_documents": [d["document"] for d in missing_docs],
            "unclear_count": unclear_count,
            "annual_income_mismatch": annual_income_mismatch,
        },
    )

    if annual_income_mismatch:
        try:
            send_annual_income_mismatch_email(
                applicant_name, sender_email, loan_category,
                declared_annual_income=annual_income_mismatch["declared"],
                thread_id=msg.get("threadId"), in_reply_to_message_id=message_id,
                submission_id=submission_id,
            )
        except Exception:
            logger.exception(
                "loan_apply documents: failed to send annual-income-mismatch follow-up to %s", sender_email
            )
            emit(
                "document_processing", "error",
                f"Failed to send annual-income-mismatch follow-up to {applicant_name}",
                submission_id=submission_id,
            )
    elif missing_docs or unclear_count:
        try:
            send_missing_documents_email(
                applicant_name, sender_email, loan_category, missing_docs,
                thread_id=msg.get("threadId"), in_reply_to_message_id=message_id,
                unclear_count=unclear_count, submission_id=submission_id,
            )
        except Exception:
            logger.exception(
                "loan_apply documents: failed to send missing-documents follow-up to %s", sender_email
            )
            emit(
                "document_processing", "error",
                f"Failed to send missing-documents follow-up to {applicant_name}",
                submission_id=submission_id,
            )
    else:
        try:
            send_documents_complete_email(
                applicant_name, sender_email, loan_category,
                thread_id=msg.get("threadId"), in_reply_to_message_id=message_id,
                submission_id=submission_id,
            )
        except Exception:
            logger.exception(
                "loan_apply documents: failed to send documents-complete confirmation to %s", sender_email
            )
            emit(
                "document_processing", "error",
                f"Failed to send documents-complete confirmation to {applicant_name}",
                submission_id=submission_id,
            )
        try:
            notify_banks_of_new_lead(submission_id)
        except Exception:
            logger.exception(
                "loan_apply documents: failed to notify banks for submission %s", submission_id
            )
            emit(
                "document_processing", "error",
                f"Failed to notify banks for {applicant_name}",
                submission_id=submission_id,
            )

    return {
        "status": "processed",
        "submission_id": submission_id,
        "documents": processed_docs,
        "extracted_data": merged_fields,
        "missing_documents": [d["document"] for d in missing_docs],
        "unclear_count": unclear_count,
        "documents_status": "documents_incomplete" if missing_docs else "documents_complete",
    }
