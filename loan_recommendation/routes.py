from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


router = APIRouter()

templates = Jinja2Templates(directory="loan_recommendation/templates")


@router.get("/loan-recommendation/page")
def loan_recommendation_page(request: Request):

    print("=" * 80)
    print("LOADING TEMPLATE: loan_recommendation/templates/loan_form.html")
    print("=" * 80)

    return templates.TemplateResponse(
        request=request,
        name="loan_form.html",
        context={}
    )