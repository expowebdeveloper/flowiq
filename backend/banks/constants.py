LOAN_TYPES = ["home_loan", "education_loan", "personal_loan", "car_loan", "gold_loan"]

MAX_DOCUMENTS = 20
MAX_DOCUMENT_SIZE = 15 * 1024 * 1024  # 15 MB per file


def parse_required_documents(text: str | None) -> list[str]:
    """Split a freeform required-documents blob into a checklist of short labels."""
    if not text:
        return []
    import re

    items = []
    for chunk in re.split(r"[;\n]|\.\s+(?=[A-Z])", text.replace("\r", "\n")):
        chunk = chunk.strip(" .")
        if chunk:
            items.append(chunk)
    return items
