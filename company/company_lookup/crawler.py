from company.company_lookup.scraper import download_website
from company.company_lookup.parser import parse_html
from company.company_lookup.extractor import extract_information


def crawl_page(url: str):

    try:

        html = download_website(url)

        parsed = parse_html(html)

        return extract_information(parsed)

    except Exception as e:

        print(f"Error crawling {url}")

        print(e)

        return None