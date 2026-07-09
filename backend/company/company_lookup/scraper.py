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

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(

            viewport={
                "width": 1366,
                "height": 768
            },

            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36"
            ),

            locale="en-US"

        )

        page = context.new_page()

        try:

            page.goto(
                url,
                wait_until="commit",
                timeout=30000
            )

            page.wait_for_load_state("domcontentloaded")

            # Give JS-heavy sites a moment to settle
            page.wait_for_timeout(2000)

            html = page.content()

        except TimeoutError:

            print(f"Timeout while loading: {url}")

            html = ""

        except Exception as e:

            print(e)

            html = ""

        finally:

            browser.close()

        return html