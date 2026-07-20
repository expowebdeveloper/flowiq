from urllib.parse import urljoin


def detect_logo(parsed_data, base_url=None):
    """
    Detect the best logo from parsed website data.

    Priority:
    1. Open Graph image
    2. Twitter image
    3. Best <img> candidate
    4. Favicon
    """

    # ----------------------------
    # Open Graph Image
    # ----------------------------
    og_image = parsed_data.get("og_image")

    if og_image:
        return make_absolute_url(og_image, base_url)

    # ----------------------------
    # Twitter Image
    # ----------------------------
    twitter_image = parsed_data.get("twitter_image")

    if twitter_image:
        return make_absolute_url(twitter_image, base_url)

    # ----------------------------
    # Score all images
    # ----------------------------
    images = parsed_data.get("images", [])

    best_logo = None
    best_score = -1

    positive_keywords = [
        "logo",
        "brand",
        "navbar",
        "header",
        "icon",
    ]

    negative_keywords = [
        "banner",
        "hero",
        "product",
        "team",
        "blog",
        "news",
        "slider",
        "gallery",
        "cover",
    ]

    for image in images:

        score = 0

        src = image.get("src", "")
        alt = image.get("alt", "")
        css_class = image.get("class", "")
        image_id = image.get("id", "")

        search_text = (
            f"{src} {alt} {css_class} {image_id}"
        ).lower()

        # Positive keywords
        for keyword in positive_keywords:
            if keyword in search_text:
                score += 10

        # Negative keywords
        for keyword in negative_keywords:
            if keyword in search_text:
                score -= 5

        # Prefer SVG
        if src.lower().endswith(".svg"):
            score += 5

        # Prefer PNG
        if src.lower().endswith(".png"):
            score += 3

        # Keep highest scoring image
        if score > best_score:
            best_score = score
            best_logo = src

    if best_logo:
        return make_absolute_url(best_logo, base_url)

    # ----------------------------
    # Favicon
    # ----------------------------
    favicon = parsed_data.get("favicon")

    if favicon:
        return make_absolute_url(favicon, base_url)

    return None


def make_absolute_url(url, base_url=None):

    if not url:
        return None

    if url.startswith("http://") or url.startswith("https://"):
        return url

    if base_url:
        return urljoin(base_url, url)

    return url