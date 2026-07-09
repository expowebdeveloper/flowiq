from company.company_lookup.search import find_official_website
from company.company_lookup.scraper import download_website
from company.company_lookup.parser import parse_html
from company.company_lookup.extractor import extract_information
from company.company_lookup.logo_detector import detect_logo


def get_website_information(company_name: str):

    # Find official website
    website = find_official_website(company_name)

    if website["website"] is None:
        return None

    # Download homepage
    html = download_website(website["website"])

    # Parse HTML
    parsed = parse_html(html)

    # Extract information
    result = extract_information(parsed)
    
    result["company_name"] = company_name

    # Add website
    result["website"] = website["website"]

    # Detect logo
    result["logo"] = detect_logo(
        parsed_data=parsed,
        base_url=website["website"]
    )

    return result


def get_website_information_from_url(
    company_name: str,
    website: str
):

    # Download homepage
    html = download_website(website)

    # Parse HTML
    parsed = parse_html(html)

    # Extract information
    result = extract_information(parsed)

    result["company_name"] = company_name

    result["website"] = website

    # Detect logo
    result["logo"] = detect_logo(
        parsed_data=parsed,
        base_url=website
    )

    return result