import json
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from db import LoanApplyDocument, UserFormSubmission, get_session
from loan_apply.requirements import get_required_documents

_styles = getSampleStyleSheet()
_title_style = ParagraphStyle("PdfTitle", parent=_styles["Title"], fontSize=18, spaceAfter=2)
_subtitle_style = ParagraphStyle("PdfSubtitle", parent=_styles["Normal"], fontSize=10, textColor=colors.grey)
_section_style = ParagraphStyle(
    "PdfSection", parent=_styles["Heading2"], fontSize=13, spaceBefore=16, spaceAfter=6,
    textColor=colors.HexColor("#1a1a2e"),
)


def _field(label: str, value) -> list[str]:
    return [label, "-" if value in (None, "") else str(value)]


def build_applicant_pdf(submission_id: str) -> bytes:
    """
    Renders one UserFormSubmission (an applicant lead) and its uploaded/verified
    documents into a single-page-ish PDF a bank can view from a notification —
    personal details, loan details, extracted fields, and document checklist
    status. Raises ValueError if the submission no longer exists (e.g. the
    lead was deleted after the bank was notified about it).
    """
    session = get_session()
    try:
        submission = session.get(UserFormSubmission, submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")

        documents = (
            session.query(LoanApplyDocument)
            .filter(LoanApplyDocument.submission_id == submission_id)
            .order_by(LoanApplyDocument.uploaded_at.asc())
            .all()
        )

        extracted_data = json.loads(submission.extracted_data) if submission.extracted_data else {}
        required_info = get_required_documents(submission.loan_type)
        required_docs = required_info["general_documents"] + required_info["category_documents"]

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=18 * mm, bottomMargin=18 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
        )
        story = []

        story.append(Paragraph("Loan Applicant Details", _title_style))
        story.append(Paragraph(
            f"Generated {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')} &middot; "
            f"Submission ID {submission.id}",
            _subtitle_style,
        ))

        story.append(Paragraph("Personal Details", _section_style))
        personal_rows = [
            _field("Full Name", f"{submission.first_name} {submission.last_name}"),
            _field("Email", submission.email),
            _field("Phone Number", submission.phone_number),
            _field("Date of Birth", submission.date_of_birth),
            _field("Gender", submission.gender),
            _field("Marital Status", submission.marital_status),
            _field("Citizenship Status", submission.citizenship_status),
            _field("Current Address", submission.current_address),
            _field("Zip Code", submission.zip_code),
        ]
        story.append(_make_table(personal_rows))

        story.append(Paragraph("Loan Details", _section_style))
        loan_rows = [
            _field("Loan Type", required_info["category"]),
            _field("Requested Amount", submission.loan_amount),
            _field("FICO Score", submission.fico_score),
            _field("Extra Details", submission.extra_loan_details),
            _field("Documents Status", submission.documents_status),
        ]
        story.append(_make_table(loan_rows))

        if extracted_data:
            story.append(Paragraph("Extracted Application Fields", _section_style))
            extracted_rows = [_field(key.replace("_", " ").title(), value) for key, value in extracted_data.items()]
            story.append(_make_table(extracted_rows))

        story.append(Paragraph("Required Documents", _section_style))
        submitted_labels = {d.label for d in documents if d.label and d.content_verified is True}
        checklist_rows = [["Document", "Status"]]
        for req in required_docs:
            name = req["document"]
            checklist_rows.append([name, "Received & verified" if name in submitted_labels else "Missing"])
        story.append(_make_table(checklist_rows, header=True))

        if documents:
            story.append(Paragraph("Uploaded Files", _section_style))
            file_rows = [["Filename", "Matched Document", "Verified"]]
            for d in documents:
                file_rows.append([
                    d.filename,
                    d.label or "Unmatched",
                    "Yes" if d.content_verified else ("No" if d.content_verified is False else "Not checked"),
                ])
            story.append(_make_table(file_rows, header=True))

        doc.build(story)
        return buffer.getvalue()
    finally:
        session.close()


def _make_table(rows: list[list[str]], header: bool = False) -> Table:
    wrapped = [
        [Paragraph(str(cell), _styles["BodyText"]) for cell in row]
        for row in rows
    ]
    table = Table(wrapped, colWidths=[55 * mm, 110 * mm] if not header else None, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f5")))
        style.append(("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"))
    else:
        style.append(("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f7f7fa")))
        style.append(("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    return table
