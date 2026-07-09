import re

import phonenumbers
from phonenumbers import PhoneNumberMatcher

EMAIL_REGEX = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE_REGEX = r"(?:\+?\d[\d\s().-]{7,}\d)"


def extract_emails(text):

    emails = re.findall(
        EMAIL_REGEX,
        text
    )

    return sorted(list(set(emails)))

def extract_phones(text):

    phones = []

    try:

        for match in PhoneNumberMatcher(text, None):

            number = match.number

            # Accept only valid numbers
            if not phonenumbers.is_valid_number(number):
                continue

            formatted = phonenumbers.format_number(
                number,
                phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )

            phones.append(formatted)

    except Exception as e:

        print(e)

    return sorted(list(set(phones)))


def extract_social_links(links):

    social = {
        "linkedin": None,
        "facebook": None,
        "twitter": None,
        "instagram": None
    }

    for link in links:

        href = link["href"].lower()

        if "linkedin.com" in href:
            social["linkedin"] = link["href"]

        elif "facebook.com" in href:
            social["facebook"] = link["href"]

        elif "twitter.com" in href or "x.com" in href:
            social["twitter"] = link["href"]

        elif "instagram.com" in href:
            social["instagram"] = link["href"]

    return social

def extract_important_pages(links):

    pages = {
        "contact": None,
        "about": None,
    }

    for link in links:

        href = link["href"].strip()
        text = link["text"].strip().lower()
        href_lower = href.lower()

        # ----------------------------
        # Contact Page
        # ----------------------------
        if pages["contact"] is None:

            if (
                text == "contact"
                or text == "contact us"
                or "/contact" in href_lower
            ):
                pages["contact"] = href

        # ----------------------------
        # About Page
        # ----------------------------
        if pages["about"] is None:

            if (
                text == "about"
                or text == "about us"
                or href_lower.endswith("/about")
                or href_lower.endswith("/about/")
                or "/about-us" in href_lower
            ):
                pages["about"] = href

    return pages


# def extract_logo(images):

#     for image in images:

#         lower = image.lower()

#         if "logo" in lower:

#             return image

#     return None

def extract_information(parsed_data):

    industry = extract_industry(parsed_data)

    print("=" * 50)
    print("Extracted Industry:", industry)
    print("=" * 50)

    return {

        "company_name": parsed_data["title"],

        "description": parsed_data["description"],

        "industry": industry,

        "emails": extract_emails(parsed_data["text"]),

        "phones": extract_phones(parsed_data["text"]),

        "social": extract_social_links(parsed_data["links"]),

        "pages": extract_important_pages(parsed_data["links"]),

        "logo": None

    }

def extract_industry(parsed_data):

    text = (
        parsed_data.get("title", "") + " " +
        parsed_data.get("keywords", "") + " " +
        parsed_data.get("description", "") + " " +
        " ".join(parsed_data.get("headings", [])) + " " +
        parsed_data.get("text", "")
    ).lower()

    # ---------------------------------
    # Quick industry detection
    # ---------------------------------
    if "technology company" in text:
        return "Technology"

    if "information technology" in text:
        return "Technology"

    if "software company" in text:
        return "Technology"

    if "software" in text:
        return "Technology"

    industries = {
        "Technology": [
            "microsoft",
            "software",
            "technology",
            "windows",
            "azure",
            "cloud",
            "copilot",
            "teams",
            "github",
            "computer"
        ],
        "Banking": [
            "bank",
            "banking"
        ],
        "Finance": [
            "finance",
            "investment",
            "fintech"
        ],
        "Healthcare": [
            "hospital",
            "medical",
            "healthcare"
        ],
        "Education": [
            "education",
            "learning",
            "school",
            "university"
        ],
        "Retail": [
            "retail",
            "shopping",
            "ecommerce"
        ],
        "Telecommunications": [
            "telecom",
            "mobile",
            "network"
        ],
        "Automotive": [
            "automotive",
            "vehicle",
            "car"
        ]
    }

    for industry, words in industries.items():

        if any(word in text for word in words):
            return industry

    return None