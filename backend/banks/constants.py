LOAN_TYPES = ["home_loan", "education_loan", "personal_loan", "car_loan", "gold_loan"]


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
