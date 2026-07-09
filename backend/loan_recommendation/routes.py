import os
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

_HERE = os.path.dirname(os.path.abspath(__file__))
_DASH = os.path.join(_HERE, "..", "dashboard", "templates")
templates = Jinja2Templates(directory=[
    os.path.join(_HERE, "templates"),
    os.path.normpath(_DASH)
])


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