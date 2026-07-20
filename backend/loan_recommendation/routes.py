from fastapi import APIRouter

router = APIRouter()


@router.get("/loan-recommendation/status")
def status():
    return {
        "status": "active",
        "service": "Loan Recommendation Service"
    }