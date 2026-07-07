import requests

from playwright.sync_api import sync_playwright, TimeoutError


def download_website(url: str):

    # ----------------------------
    # First try using requests
    # ----------------------------

    try:

        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if response.status_code == 200:

            return response.text

    except Exception:

        pass

    # ----------------------------
    # Fallback to Playwright
    # ----------------------------

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        try:

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=10000
            )

        except TimeoutError:

            print(f"Timeout while loading: {url}")

        html = page.content()

        browser.close()

        return html