import io
import re

import pdfplumber
import pytesseract
from PIL import Image

AADHAAR_NUMBER_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")  # Aadhaar: always 12 digits
PAN_NUMBER_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")  # PAN: always 10 chars, e.g. ABCDE1234F
AADHAAR_KEYWORDS = (
    "aadhaar", "aadhar", "uidai", "unique identification authority", "government of india",
)
PAN_KEYWORDS = ("permanent account number", "income tax department", "pan card")

IMAGE_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

# Verhoeff algorithm tables — used by UIDAI to compute Aadhaar's trailing check digit.
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6], [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4], [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2], [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def _verhoeff_checksum_valid(number: str) -> bool:
    """Validates a 12-digit number against UIDAI's Verhoeff check-digit scheme."""
    digits = [int(d) for d in number[::-1]]
    c = 0
    for i, digit in enumerate(digits):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][digit]]
    return c == 0


def extract_pdf_text(data: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join(
                page.extract_text() or "" for page in pdf.pages
            ).strip()
    except Exception as e:
        return f"[Could not read PDF: {e}]"


def extract_image_text(data: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        return f"[Could not read image: {e}]"


def looks_like_pan(extracted_text: str) -> bool:
    """PAN is always a 10-character alphanumeric code (5 letters, 4 digits, 1 letter),
    e.g. ABCDE1234F — never 12 digits. Used to positively identify (and reject) PAN
    documents so they are never mistaken for Aadhaar."""
    text_lower = (extracted_text or "").lower()
    keyword_hit = any(k in text_lower for k in PAN_KEYWORDS)
    format_hit = bool(PAN_NUMBER_RE.search((extracted_text or "").upper()))
    return keyword_hit and format_hit


def looks_like_aadhaar(filename: str, extracted_text: str) -> bool:
    """Content-based heuristic: extracted text must contain an official Aadhaar/UIDAI
    keyword AND a 12-digit number (Aadhaar is always 12 digits, never 10) that passes
    the Verhoeff checksum used by real Aadhaar numbers. A document matching PAN's format
    (10-character alphanumeric, e.g. ABCDE1234F) is explicitly rejected even if renamed
    to look like an Aadhaar file — filename is intentionally NOT used to bypass this.
    Not OCR-grade proof, and not a substitute for real UIDAI verification."""
    if looks_like_pan(extracted_text):
        return False
    text_lower = (extracted_text or "").lower()
    keyword_hit = any(k in text_lower for k in AADHAAR_KEYWORDS)
    if not keyword_hit:
        return False
    for match in AADHAAR_NUMBER_RE.finditer(extracted_text or ""):
        candidate = re.sub(r"\s", "", match.group())
        if _verhoeff_checksum_valid(candidate):
            return True
    return False
