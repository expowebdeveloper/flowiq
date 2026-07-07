import json

from sqlalchemy.orm import Session

from company.company_lookup import crud

from company.company_lookup.schemas import CompanyLookupCreate
from company.company_lookup.crawler import crawl_page
from company.company_lookup.providers.website_provider import get_website_information
from company.company_lookup.providers.wikipedia_provider import get_wikipedia_information
from company.company_lookup.providers.merger import merge_company_information

def lookup_company(
        db: Session,
        company_name: str
    ):

    # ----------------------------
    # Check Cache
    # ----------------------------

    company = crud.get_company_by_name(
        db,
        company_name
    )

    print("Searching for:", company_name)
    print("Database result:", company)

    if company:

        return {

            "company_name": company.company_name,

            "website": company.website,

            "industry": company.industry,

            "description": company.description,

            "emails": json.loads(company.emails),

            "phones": json.loads(company.phones),

            "logo": company.logo,

            "social": {
                "linkedin": company.linkedin,
                "facebook": company.facebook,
                "twitter": company.twitter,
                "instagram": company.instagram
            },

            "pages": {
                "contact": company.contact_page,
                "about": company.about_page
            }

        }

    # ----------------------------
    # Find official website
    # ----------------------------
    website_data = get_website_information(company_name)

    if website_data is None:
        return {
            "success": False,
            "message": "Official website not found."
        }

    wikipedia_data = get_wikipedia_information(company_name)
    print("=" * 60)
    print(wikipedia_data)
    print("=" * 60)
    

    result = merge_company_information(
        website_data=website_data,
        wikipedia_data=wikipedia_data
    )

    pages = result["pages"]

    print("=" * 60)
    print("PAGES FOUND:")
    print(pages)
    print("=" * 60)

    for page_name in ["about", "contact"]:

        page_url = pages.get(page_name)

        if not page_url:
            continue

        print(f"Crawling {page_name}: {page_url}")

        try:

            try:

                page_result = crawl_page(page_url)

            except Exception as e:

                print(e)

                continue

            if page_result is None:
                continue

            result["emails"] = list(
                set(result["emails"] + page_result["emails"])
            )

            result["phones"] = list(
                set(result["phones"] + page_result["phones"])
            )

            # Update description if homepage didn't have one
            if not result["description"] and page_result["description"]:
                result["description"] = page_result["description"]

            # Update industry if homepage didn't have one
            if not result["industry"] and page_result["industry"]:
                result["industry"] = page_result["industry"]

            # Update logo if homepage didn't have one
            if not result["logo"] and page_result["logo"]:
                result["logo"] = page_result["logo"]

            # Update social links if homepage didn't have them
            for key in result["social"]:

                if not result["social"][key] and page_result["social"][key]:
                    result["social"][key] = page_result["social"][key]

        except Exception as e:

            print(f"Failed to crawl: {page_url}")
            print(e)

            continue


    # Save ONLY ONCE after crawling finishes
    crud.create_company(

        db=db,

        company=CompanyLookupCreate(

            company_name=company_name,

            website=result["website"],

            description=result["description"],

            industry=result["industry"],

            emails=result["emails"],

            phones=result["phones"],

            logo=result.get("logo"),

            linkedin=result["social"]["linkedin"],

            facebook=result["social"]["facebook"],

            twitter=result["social"]["twitter"],

            instagram=result["social"]["instagram"],

            contact_page=result["pages"]["contact"],

            about_page=result["pages"]["about"]

        )

    )

    return result