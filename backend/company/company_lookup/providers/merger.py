def merge_company_information(
    website_data: dict | None,
    wikipedia_data: dict | None
):
    """
    Merge company information from multiple providers.
    """

    website_data = website_data or {}
    wikipedia_data = wikipedia_data or {}

    return {

        "company_name": website_data.get("company_name"),

        "website": website_data.get("website"),

        "description": (
            website_data.get("description")
            or wikipedia_data.get("description")
        ),

        "industry": (
            website_data.get("industry")
            or wikipedia_data.get("industry")
        ),

        "emails": website_data.get("emails", []),

        "phones": website_data.get("phones", []),

        "logo": (
            website_data.get("logo")
            or wikipedia_data.get("logo")
        ),

        "social": website_data.get(
            "social",
            {
                "linkedin": None,
                "facebook": None,
                "twitter": None,
                "instagram": None,
            },
        ),

        "pages": website_data.get(
            "pages",
            {
                "contact": None,
                "about": None,
            },
        ),

        "founded": wikipedia_data.get("founded"),

        "headquarters": wikipedia_data.get("headquarters"),

        "founders": wikipedia_data.get("founders"),

        "employees": wikipedia_data.get("employees"),
    }