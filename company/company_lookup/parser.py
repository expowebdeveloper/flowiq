from bs4 import BeautifulSoup


def parse_html(html: str):

    soup = BeautifulSoup(html, "lxml")

    data = {}

    # ----------------------------
    # Title
    # ----------------------------
    data["title"] = (
        soup.title.get_text(strip=True)
        if soup.title
        else ""
    )

    # ----------------------------
    # Meta Description
    # ----------------------------
    meta = soup.find(
        "meta",
        attrs={"name": "description"}
    )

    data["description"] = (
        meta.get("content", "")
        if meta
        else ""
    )

    # ----------------------------
    # Meta Keywords
    # ----------------------------
    keywords = soup.find(
        "meta",
        attrs={"name": "keywords"}
    )

    data["keywords"] = (
        keywords.get("content", "")
        if keywords
        else ""
    )

    # ----------------------------
    # All Links
    # ----------------------------
    data["links"] = []

    for link in soup.find_all("a", href=True):

        data["links"].append({
            "text": link.get_text(strip=True),
            "href": link["href"]
        })

    # ----------------------------
    # Images
    # ----------------------------
    data["images"] = []

    for image in soup.find_all("img"):

        src = (
            image.get("src")
            or image.get("data-src")
            or image.get("data-lazy-src")
            or image.get("data-original")
        )

        if not src:
            continue

        data["images"].append({

            "src": src,
            "alt": image.get("alt", ""),
            "id": image.get("id", ""),
            "class": " ".join(image.get("class", [])),
            "width": image.get("width"),
            "height": image.get("height")

        })

    # ----------------------------
    # Headings
    # ----------------------------
    data["headings"] = []

    for heading in soup.find_all(["h1", "h2", "h3"]):

        text = heading.get_text(strip=True)

        if text:
            data["headings"].append(text)

    # ----------------------------
    # Meta Tags
    # ----------------------------
    data["meta"] = {}

    for meta in soup.find_all("meta"):

        key = meta.get("name") or meta.get("property")

        value = meta.get("content")

        if key and value:
            data["meta"][key] = value

    # ----------------------------
    # Footer
    # ----------------------------
    footer = soup.find("footer")

    if footer:

        data["footer"] = footer.get_text(
            separator=" ",
            strip=True
        )

    else:

        data["footer"] = ""

    # ----------------------------
    # Remove unwanted tags
    # ----------------------------
    for tag in soup([
        "script",
        "style",
        "svg",
        "noscript"
    ]):
        tag.decompose()

    # ----------------------------
    # Visible Text
    # ----------------------------
    data["text"] = soup.get_text(
        separator=" ",
        strip=True
    )

    # ----------------------------
    # Raw HTML
    # ----------------------------
    data["html"] = html

    return data