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
    "office.com"
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

    for result in results:

        url = result.get("href", "")

        if any(domain in url for domain in BLACKLIST):
            continue

        return {
            "company_name": company_name,
            "website": url
        }

    return {
        "company_name": company_name,
        "website": None
    }