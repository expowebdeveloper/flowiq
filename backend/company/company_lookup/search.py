from urllib.parse import urlparse
from ddgs import DDGS


BLACKLIST = [
    "wikipedia.org",
    "linkedin.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "support.microsoft.com",
    "office.com",
]


def find_official_website(company_name: str):

    query = f"{company_name} official website"

    with DDGS() as ddgs:

        results = list(
            ddgs.text(
                query,
                max_results=10
            )
        )

    company = company_name.lower().replace(" ", "")

    best_url = None
    best_score = -1

    for result in results:

        url = result.get("href", "")

        if not url:
            continue

        if any(domain in url.lower() for domain in BLACKLIST):
            continue

        hostname = urlparse(url).netloc.lower()

        score = 0

        # Prefer root domain
        if hostname.startswith("www."):
            hostname = hostname[4:]

        if hostname.count(".") == 1:
            score += 50

        # Company name in domain
        if company in hostname.replace("-", "").replace(".", ""):
            score += 100

        # Penalize subdomains
        if hostname.count(".") > 1:
            score -= 20

        if score > best_score:
            best_score = score
            best_url = url

    return {
        "company_name": company_name,
        "website": best_url
    }


def search_companies(company_name: str):

    query = f"{company_name}"

    matches = []

    with DDGS() as ddgs:

        results = list(
            ddgs.text(
                query,
                max_results=10
            )
        )

    for result in results:

        url = result.get("href", "")

        title = result.get("title", "")

        SEARCH_BLACKLIST = [
            "carwale.com",
            "cardekho.com",
            "91mobiles.com",
            "ambitionbox.com",
            "glassdoor.com",
            "indeed.com",
            "justdial.com",
            "indiamart.com",
            "tradeindia.com",
            "crunchbase.com"
        ]

        if not url:
            continue

        if any(domain in url.lower() for domain in BLACKLIST):
            continue

        if any(domain in url.lower() for domain in SEARCH_BLACKLIST):
            continue

        matches.append({

            "name": title,

            "website": url

        })

    return {

        "company_name": company_name,

        "matches": matches

    }