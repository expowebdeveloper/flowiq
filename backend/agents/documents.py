import io
import re
from difflib import SequenceMatcher

import cv2
import numpy as np
import pdfplumber
import pytesseract
from PIL import Image

IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")  # IFSC: 4 bank letters + literal '0' + 6 branch chars
HUID_RE = re.compile(r"\b[A-Z0-9]{6}\b")  # Hallmark Unique ID: 6-char alphanumeric

# Still used by looks_like_aadhaar/looks_like_pan below, which back the
# separate KYC upload flow's aadhaar_verified check (see kyc/routes.py) — kept
# even though the loan-apply document pipeline no longer requests either
# document type via require.json.
AADHAAR_KEYWORDS = (
    "aadhaar", "aadhar", "uidai", "unique identification authority", "government of india",
)
PAN_KEYWORDS = ("permanent account number", "income tax department", "pan card")

IMAGE_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

_FACE_CASCADE_PATH = f"{cv2.data.haarcascades}haarcascade_frontalface_default.xml"
_FACE_CASCADE = cv2.CascadeClassifier(_FACE_CASCADE_PATH)


def extract_pdf_text(data: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join(
                page.extract_text() or "" for page in pdf.pages
            ).strip()
    except Exception as e:
        return f"[Could not read PDF: {e}]"


def _preprocess_for_ocr(data: bytes) -> np.ndarray | None:
    """
    Upscales + denoises + adaptively thresholds an image before OCR — plain
    pytesseract.image_to_string on a small, low-res photo/screenshot (common
    for ID documents forwarded by email, as opposed to a proper flatbed scan)
    frequently produces unusable garbled text. This meaningfully improves
    keyword-detection accuracy for looks_like_aadhaar/looks_like_pan/etc. on
    such images, though it does not guarantee an exact character-for-character
    read of ID numbers, which OCR error can still corrupt regardless.
    """
    try:
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        gray = cv2.resize(gray, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
        )
    except Exception:
        return None


def extract_image_text_candidates(data: bytes) -> list[str]:
    """
    Runs OCR under a few different page-segmentation configurations — default
    layout (psm 3) on the raw image, single-column/table mode (psm 4) on the
    raw image, and default layout on a preprocessed (upscaled/denoised/
    thresholded) version — and returns every non-empty reading. Different
    documents (and even different rows of the same tabular document) read
    best under different configurations: psm 3 more reliably keeps a
    multi-word field like "VEHICLE MODEL: ..." on one logical line, while psm
    4 more reliably keeps a narrow table's label/amount pairs from being torn
    apart. Callers that need best-effort structured fields (e.g.
    field_extraction.extract_vehicle_fields) should search across all
    candidates rather than just one, since no single pass is uniformly best.
    """
    candidates: list[str] = []
    try:
        image = Image.open(io.BytesIO(data))
        candidates.append(pytesseract.image_to_string(image).strip())
        candidates.append(pytesseract.image_to_string(image, config="--psm 4").strip())
    except Exception:
        pass

    preprocessed = _preprocess_for_ocr(data)
    if preprocessed is not None:
        try:
            candidates.append(pytesseract.image_to_string(preprocessed, config="--psm 6").strip())
        except Exception:
            pass

    return [c for c in candidates if c]


def extract_image_text(data: bytes) -> str:
    """
    Single best-effort text reading for an image — picks whichever OCR
    candidate (see extract_image_text_candidates) captured the most text, as
    a proxy for completeness. Used by callers that only need one text blob
    to search (document-type validators, Aadhaar/PAN number extraction);
    callers that need structured multi-field extraction from a tabular
    document should use extract_image_text_candidates directly instead, since
    picking a single "best" text loses fields that only a different pass
    read correctly.
    """
    candidates = extract_image_text_candidates(data)
    best = max(candidates, key=len, default="")
    if best:
        return best
    try:
        Image.open(io.BytesIO(data))
    except Exception as e:
        return f"[Could not read image: {e}]"
    return ""


def _keyword_hit(text: str, keywords: tuple[str, ...], min_hits: int = 1) -> bool:
    text_lower = (text or "").lower()
    return sum(1 for k in keywords if k in text_lower) >= min_hits


def _fuzzy_keyword_hit(text: str, keywords: tuple[str, ...], threshold: float = 0.6) -> bool:
    """
    Tolerant version of a keyword substring check, for OCR text pulled from
    low-res/compressed images (e.g. ID photos forwarded by email rather than
    scanned) where an exact phrase like "permanent account number" often comes
    back garbled ("feomaec Account ie tey"). Slides a same-length window across
    the text and accepts a keyword as present if any window is at least
    `threshold` similar to it — looser than an exact substring match, but still
    requires the keyword's general shape to actually appear, not just any text.

    Short (<=2-word) keywords use a higher effective threshold: a 2-token
    window like "pan :" is already 62% similar to "pan card" by pure
    character overlap, which false-positived on an unrelated form's "Customer
    PAN" field label. Longer keywords (3+ words, e.g. "permanent account
    number") are far more distinctive and can safely stay at the base
    threshold.
    """
    text_lower = (text or "").lower()
    if not text_lower:
        return False
    words = text_lower.split()
    for keyword in keywords:
        if keyword in text_lower:
            return True
        keyword_words = len(keyword.split())
        effective_threshold = threshold if keyword_words >= 3 else max(threshold, 0.85)
        for i in range(len(words) - keyword_words + 1):
            window = " ".join(words[i : i + keyword_words])
            if SequenceMatcher(None, window, keyword).ratio() >= effective_threshold:
                return True
    return False


def looks_like_pan(extracted_text: str) -> bool:
    """Identifies a PAN card by its official keywords alone (e.g. "Permanent Account
    Number", "Income Tax Department") — used to positively identify (and reject) PAN
    documents so they are never mistaken for Aadhaar. Keyword matching is fuzzy
    (tolerant of OCR noise)."""
    return _fuzzy_keyword_hit(extracted_text, PAN_KEYWORDS)


def looks_like_aadhaar(filename: str, extracted_text: str) -> bool:
    """Identifies an Aadhaar card by its official Aadhaar/UIDAI keywords alone — used to
    positively identify (and reject) Aadhaar documents so they are never mistaken for
    PAN. A document matching PAN's keywords is explicitly rejected even if renamed to
    look like an Aadhaar file — filename is intentionally NOT used to bypass this.
    Keyword matching is fuzzy (tolerant of OCR noise)."""
    if looks_like_pan(extracted_text):
        return False
    return _fuzzy_keyword_hit(extracted_text, AADHAAR_KEYWORDS)


PHOTO_ID_KEYWORDS = (
    "driver license", "driver's license", "drivers license", "identification card",
    "department of motor vehicles", "class d", "passport", "state id",
)


def validate_photo_id(extracted_text: str) -> bool:
    """Heuristic: US driver's licenses/state IDs name the issuing authority ("Department
    of Motor Vehicles"/state name) or say "driver license"/"identification card", and
    print a DOB and a license class/expiration alongside it — passports instead print
    "passport" plus a document/passport number. Not a substitute for real ID
    verification, just a structural signal this is a government photo ID and not some
    other document. Keyword matching is fuzzy (tolerant of OCR noise)."""
    text_lower = (extracted_text or "").lower()
    has_id_keyword = _fuzzy_keyword_hit(text_lower, PHOTO_ID_KEYWORDS)
    has_id_structure = _keyword_hit(text_lower, ("dob", "date of birth", "exp", "class", "sex", "iss"), min_hits=1)
    return has_id_keyword and (has_id_structure or "passport" in text_lower)


SSN_CARD_RE = re.compile(r"\b\d{3}[\s\-]?\d{2}[\s\-]?\d{4}\b")  # SSN: always 9 digits, XXX-XX-XXXX (OCR sometimes misreads the dash as a space)

# Phrases that appear ONLY on the card itself, never on a pay stub/tax form
# that merely references a Social Security number in passing (which instead
# says things like "Social Security Tax Withheld" or "Employee SSN") — each
# checked individually (rather than as one fuzzy-matched tuple) since a
# shared "social security" prefix across an unrelated multi-word phrase can
# otherwise drag a whole-tuple SequenceMatcher ratio high enough to false-hit.
SSN_CARD_DISTINCTIVE_KEYWORDS = ("has been established for", "not for identification")


def validate_ssn_card(extracted_text: str) -> bool:
    """Heuristic: identifies a Social Security card by its distinctive official framing
    alone ("has been established for", "not for identification") — found nowhere else,
    so a pay stub/W-2/tax form that merely references a Social Security number in
    passing is never mistaken for the card itself. Does NOT also require the 9-digit
    number to be present/well-formed: real phone-photographed cards routinely OCR the
    printed number worse than the surrounding text (low resolution, glare, angle), so
    gating identification on it would reject genuine cards the way looks_like_aadhaar/
    looks_like_pan/validate_photo_id don't for their own ID numbers. The number is
    still extracted separately, best-effort, by extract_ssn_card_fields. Keyword
    matching is fuzzy (tolerant of OCR noise); threshold=0.8 (above the 0.6 default)
    since these 3-word phrases need to be genuinely close to the card's actual wording,
    not just share a word with an unrelated phrase (e.g. "identification number" on a
    W-2's EIN line otherwise fuzzy-matches "not for identification" at the default
    threshold)."""
    text_lower = (extracted_text or "").lower()
    return any(_fuzzy_keyword_hit(text_lower, (kw,), threshold=0.8) for kw in SSN_CARD_DISTINCTIVE_KEYWORDS)


def validate_selfie(image_data: bytes) -> bool:
    """No OCR possible on a plain photo — instead runs Haar-cascade face detection to
    confirm the image actually contains a human face, rather than a blank/random image."""
    try:
        arr = np.frombuffer(image_data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False
        faces = _FACE_CASCADE.detectMultiScale(img, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        return len(faces) > 0
    except Exception:
        return False


def validate_gold_valuation_certificate(extracted_text: str) -> bool:
    """Heuristic: real BIS-hallmark-based valuation certificates state carat/fineness
    (e.g. '22K916' / '18K750'), a 6-char HUID code, and purity/hallmark terminology."""
    text_lower = (extracted_text or "").lower()
    has_keyword = _keyword_hit(text_lower, (
        "gold", "valuation", "purity", "hallmark", "carat", "karat", "huid", "bis",
    ), min_hits=2)
    has_carat_fineness = bool(re.search(r"\b(1[0-9]|2[0-4])\s?k\s?\d{3}\b", text_lower))
    has_huid = bool(HUID_RE.search((extracted_text or "").upper())) and "huid" in text_lower
    return has_keyword and (has_carat_fineness or has_huid or "carat" in text_lower or "karat" in text_lower)


def validate_property_title_deed(extracted_text: str) -> bool:
    """Heuristic: title deeds reference registration/sub-registrar filings and ownership
    transfer language, per India's Registration Act framework."""
    text_lower = (extracted_text or "").lower()
    return _keyword_hit(text_lower, (
        "title deed", "sale deed", "sub-registrar", "sub registrar", "registration act",
        "conveyance", "ownership", "survey number", "khata",
    ), min_hits=1)


def validate_sale_agreement(extracted_text: str) -> bool:
    """Heuristic: sale agreements reference the parties, consideration amount, and
    stamp duty/registration terms typical of Indian property sale agreements."""
    text_lower = (extracted_text or "").lower()
    has_agreement_terms = _keyword_hit(text_lower, ("agreement to sell", "sale agreement", "vendor", "purchaser"), min_hits=1)
    has_transaction_terms = _keyword_hit(text_lower, ("stamp duty", "consideration", "registration", "possession"), min_hits=1)
    return has_agreement_terms and has_transaction_terms


def validate_salary_slip(extracted_text: str) -> bool:
    """Heuristic: Indian payslips always break down earnings/deductions and state a net
    payable figure, per the Payment of Wages Act's disclosure requirements."""
    text_lower = (extracted_text or "").lower()
    has_identity_terms = _keyword_hit(text_lower, ("payslip", "pay slip", "salary slip"), min_hits=1)
    has_breakdown_terms = _keyword_hit(text_lower, (
        "gross pay", "gross salary", "net pay", "net salary", "basic salary", "hra",
        "deduction", "provident fund", "pf", "tds",
    ), min_hits=2)
    return has_identity_terms or has_breakdown_terms


def validate_pay_stub(extracted_text: str) -> bool:
    """Heuristic: US pay stubs/earnings statements name themselves as such and print a
    pay/reporting period plus a year-to-date breakdown — distinct from validate_salary_slip's
    India-specific payslip terminology (HRA/PF/TDS), since "Recent Pay Stubs" and "Latest N
    Months Salary Slips" are separate document requirements for different loan categories."""
    text_lower = (extracted_text or "").lower()
    has_identity_terms = _keyword_hit(text_lower, ("pay stub", "paystub", "earnings statement"), min_hits=1)
    has_structure_terms = _keyword_hit(text_lower, (
        "pay period", "reporting period", "pay date", "ytd", "year to date", "current pay",
        "gross pay", "net pay",
    ), min_hits=2)
    return has_identity_terms or has_structure_terms


EIN_RE = re.compile(r"\b\d{2}-\d{7}\b")  # Employer Identification Number: XX-XXXXXXX


def validate_w2(extracted_text: str) -> bool:
    """Heuristic: IRS Form W-2 names itself ("Wage and Tax Statement" / "Form W-2") and
    prints an EIN in the IRS's distinctive XX-XXXXXXX format alongside its numbered-box
    wage/withholding terminology — a much more specific structural signature than a
    generic pay stub, so this is checked as its own document type rather than folded
    into validate_pay_stub."""
    text_lower = (extracted_text or "").lower()
    has_identity_terms = _keyword_hit(text_lower, ("w-2", "w2 form", "wage and tax statement"), min_hits=1)
    has_box_terms = _keyword_hit(text_lower, (
        "wages, tips", "employer identification", "social security wages", "medicare wages",
        "federal income tax withheld",
    ), min_hits=1)
    has_ein_shape = bool(EIN_RE.search(extracted_text or ""))
    return has_identity_terms and (has_box_terms or has_ein_shape)


def validate_bank_statement(extracted_text: str) -> bool:
    """Heuristic: RBI mandates IFSC printed on every Indian bank statement — requiring
    it (rather than a looser "account number" + "statement" keyword pair, which a US
    statement also satisfies) keeps this validator from ever matching the unrelated
    US-format validate_us_bank_statement's documents even if a future loan category
    ends up requesting both labels together."""
    text_lower = (extracted_text or "").lower()
    has_ifsc = bool(IFSC_RE.search((extracted_text or "").upper()))
    has_ifsc_keyword = "ifsc" in text_lower
    return has_ifsc or has_ifsc_keyword


ROUTING_NUMBER_RE = re.compile(r"\brouting\s*(?:number|no\.?|#)?\s*[:\-]?\s*(\d{9})\b", re.IGNORECASE)


def validate_us_bank_statement(extracted_text: str) -> bool:
    """Heuristic: US bank statements print a 9-digit ABA routing number and/or an
    account number alongside a statement period and balance — distinct from
    validate_bank_statement's IFSC-based check, since "Bank Statements" (US) and the
    older "N Months Bank Statement" labels (India) are separate document requirements
    for different loan categories.

    Also accepts a looser "generic bank statement" shape (an account/statement
    identifier plus a running transaction ledger with debit/credit/balance
    columns) so a real statement from a bank that doesn't use US-specific
    terms — e.g. an Indian bank statement whose "IFS Code" OCR'd too poorly
    for validate_bank_statement's IFSC check to catch — still isn't rejected
    outright as "not a bank statement" just because it isn't US-branded.
    Applicants only ever have one actual bank statement to send, so a false
    positive here (accepting a non-statement) matters far less than false-
    negatives forcing a real statement through repeated re-uploads."""
    text_lower = (extracted_text or "").lower()
    has_routing = bool(ROUTING_NUMBER_RE.search(extracted_text or ""))
    has_account_terms = _keyword_hit(
        text_lower, ("account number", "account no", "statement period", "beginning balance", "ending balance"),
        min_hits=2,
    )
    has_statement_identity = _keyword_hit(
        text_lower, ("account statement", "bank statement", "statement of account"), min_hits=1,
    )
    has_ledger_terms = _keyword_hit(
        text_lower, ("debit", "credit", "balance", "txn date", "transaction date"), min_hits=2,
    )
    has_generic_statement_shape = has_statement_identity and has_ledger_terms
    return has_routing or has_account_terms or has_generic_statement_shape


def validate_tax_return(extracted_text: str) -> bool:
    """Heuristic: IRS Form 1040 names itself ("Form 1040" / "U.S. Individual Income Tax
    Return") and prints its distinctive line-item terminology (adjusted gross income,
    filing status, wages and salaries) — a specific enough signature that this isn't
    confused with a W-2 or pay stub, which report similar wage figures but never use
    1040-specific line-item language."""
    text_lower = (extracted_text or "").lower()
    has_identity_terms = _fuzzy_keyword_hit(text_lower, ("form 1040", "u.s. individual income tax return"), threshold=0.75)
    has_1040_terms = _keyword_hit(
        text_lower, ("adjusted gross income", "filing status", "wages, salaries", "wages/salaries"), min_hits=1,
    )
    return has_identity_terms or has_1040_terms


def validate_purchase_agreement(extracted_text: str) -> bool:
    """Heuristic: a purchase agreement/sales contract names itself as such and states
    the parties (seller/buyer or customer) plus a total/purchase price — distinct from
    validate_sale_agreement's India-specific property-transfer terminology (stamp duty,
    consideration, possession), since "Purchase Agreement / Sales Contract" is a
    separate document requirement from the older "Sale Agreement" label."""
    text_lower = (extracted_text or "").lower()
    has_identity_terms = _keyword_hit(text_lower, ("purchase agreement", "sales contract"), min_hits=1)
    has_party_terms = _keyword_hit(text_lower, ("seller", "buyer", "customer"), min_hits=1)
    has_price_terms = _keyword_hit(text_lower, ("total price", "purchase price", "total purchase"), min_hits=1)
    return has_identity_terms and (has_party_terms or has_price_terms)


def validate_down_payment_proof(extracted_text: str) -> bool:
    """Heuristic: a down-payment funds letter names itself as a funds/down-payment
    certification (not a plain bank statement — this is a bank-issued letter
    specifically certifying money is set aside for a closing) and states a total
    available funds figure alongside a designated down-payment amount."""
    text_lower = (extracted_text or "").lower()
    has_identity_terms = _fuzzy_keyword_hit(
        text_lower, ("verification of funds", "down payment funds", "proof of down payment"), threshold=0.75,
    )
    has_funds_terms = _keyword_hit(text_lower, ("total available funds", "designated", "available funds"), min_hits=1)
    return has_identity_terms and has_funds_terms


def validate_homeowners_insurance(extracted_text: str) -> bool:
    """Heuristic: a homeowners insurance declarations page names itself as such
    ("policy declarations", "declarations page") and prints its distinctive
    structure — coverage sections, a deductible, and a premium — none of which
    appear together on an unrelated document."""
    text_lower = (extracted_text or "").lower()
    has_identity_terms = _keyword_hit(
        text_lower, ("policy declarations", "declarations page", "homeowners policy", "home owners policy"), min_hits=1,
    )
    has_policy_terms = _keyword_hit(text_lower, ("dwelling", "deductible", "policy premium", "coverage"), min_hits=2)
    return has_identity_terms and has_policy_terms


def validate_property_appraisal(extracted_text: str) -> bool:
    """Heuristic: a property appraisal report names itself as such and states an
    appraised value alongside licensed-appraiser terminology — distinct from a
    plain property listing/valuation estimate that lacks the report's formal
    certification language."""
    text_lower = (extracted_text or "").lower()
    has_identity_terms = _keyword_hit(text_lower, ("appraisal report", "property appraisal"), min_hits=1)
    has_valuation_terms = _keyword_hit(
        text_lower, ("appraised value", "market value", "comparable sales", "appraiser"), min_hits=1,
    )
    return has_identity_terms and has_valuation_terms


def validate_admission_letter(extracted_text: str) -> bool:
    """Heuristic: admission/offer letters name the institution, course, and academic
    year/session being admitted into."""
    text_lower = (extracted_text or "").lower()
    has_admission_terms = _keyword_hit(text_lower, ("admission", "offer letter", "admitted", "enrolled", "enrollment"), min_hits=1)
    has_institution_terms = _keyword_hit(text_lower, ("college", "university", "institute", "school", "course", "programme", "program"), min_hits=1)
    return has_admission_terms and has_institution_terms


def validate_fee_structure_document(extracted_text: str) -> bool:
    """Heuristic: fee structure sheets itemize tuition/other fees with an academic
    year/term and a total payable amount."""
    text_lower = (extracted_text or "").lower()
    has_fee_terms = _keyword_hit(text_lower, ("fee structure", "tuition fee", "fees payable", "total fee", "semester fee"), min_hits=1)
    has_breakdown_terms = _keyword_hit(text_lower, ("tuition", "hostel", "semester", "academic year", "total"), min_hits=1)
    return has_fee_terms or (has_breakdown_terms and "fee" in text_lower)


# Maps the exact document labels used in json/require.json and bank required_documents
# lists to a (needs_image_bytes, validator) pair. Text-based validators receive OCR/PDF
# extracted text; validate_selfie receives raw image bytes directly (no OCR possible).
DOCUMENT_VALIDATORS = {
    "aadhaar card": ("text", looks_like_aadhaar),
    "government-issued photo id": ("text", validate_photo_id),
    "social security number (ssn)": ("text", validate_ssn_card),
    "recent pay stubs": ("text", validate_pay_stub),
    "w-2 forms": ("text", validate_w2),
    "federal tax returns": ("text", validate_tax_return),
    "bank statements": ("text", validate_us_bank_statement),
    "purchase agreement / sales contract": ("text", validate_purchase_agreement),
    "proof of down payment funds": ("text", validate_down_payment_proof),
    "homeowners insurance declaration page": ("text", validate_homeowners_insurance),
    "property appraisal report": ("text", validate_property_appraisal),
    "selfie": ("image", validate_selfie),
    "gold valuation certificate": ("text", validate_gold_valuation_certificate),
    "property title deeds": ("text", validate_property_title_deed),
    "sale agreement": ("text", validate_sale_agreement),
    "latest 3 months salary slips": ("text", validate_salary_slip),
    "latest 2 months salary slips": ("text", validate_salary_slip),
    "6 months bank account statement": ("text", validate_bank_statement),
    "6 months bank statement of salary account": ("text", validate_bank_statement),
    "3 months bank statement": ("text", validate_bank_statement),
    "6 months bank statement": ("text", validate_bank_statement),
    "admission letter": ("text", validate_admission_letter),
    "fee structure document": ("text", validate_fee_structure_document),
}
