from db import get_db
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from company.models import Company
from company.company_lookup.search import find_official_website
from company.company_lookup.scraper import download_website
from company.company_lookup.parser import parse_html
from company.company_lookup.extractor import extract_information
from company.company_lookup.services import lookup_company
from company.company_lookup.crawler import crawl_page
from company.company_lookup.search import search_companies
from company.company_lookup.search import search_companies

router = APIRouter(
    prefix="/company-lookup",
    tags=["Company Lookup"]
)

@router.get("/exists")
def company_exists(
    company: str,
    db: Session = Depends(get_db)
):
    company_obj = (
        db.query(Company)
        .filter(Company.company_name == company)
        .first()
    )

    return {
        "exists": company_obj is not None
    }

@router.get("/search")
def search(
    q: str = Query(...)
):
    return find_official_website(q)


@router.get("/download")
def download(
    url: str
):

    html = download_website(url)

    return {
        "html": html[:3000]
    }


@router.get("/parse")
def parse(
    url: str
):

    html = download_website(url)

    return parse_html(html)


@router.get("/extract")
def extract(
    url: str
):

    html = download_website(url)

    parsed = parse_html(html)

    return extract_information(parsed)


@router.get("/lookup")
def lookup(

    company: str,

    website: str | None = None,

    db: Session = Depends(get_db)

):

    return lookup_company(

        db=db,

        company_name=company,

        website=website

    )

@router.get("/crawl")
def crawl(
    url: str
):

    return crawl_page(url)


@router.get("/search-companies")
def search_company(
    q: str = Query(...)
):
    return search_companies(q)

@router.get("/lookup-search")
def lookup_search(
    company: str
):
    return search_companies(company)