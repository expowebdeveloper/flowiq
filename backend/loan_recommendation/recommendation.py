from fastapi import APIRouter
from loan_recommendation.schemas import (
    LoanRecommendationRequest,
    LoanRecommendationResponse,
    RecommendedBank,
)
from loan_recommendation.services import RecommendationService
from sqlalchemy.orm import Session
from fastapi import Depends
from db import get_db


router = APIRouter(
    prefix="/loan-recommendation",
    tags=["Loan Recommendation"]
)

recommendation_service = RecommendationService()


@router.post(
    "/recommend",
    response_model=LoanRecommendationResponse
)
def recommend_loan(
    request: LoanRecommendationRequest,
    db: Session = Depends(get_db)
):

    result = recommendation_service.recommend(
        db,
        request
    )

    print("=" * 80)
    print(type(result))
    print(result)
    print("=" * 80)

    response = LoanRecommendationResponse(

        recommendations=[
            RecommendedBank(**bank)
            for bank in result["recommendations"]
        ],

        rejected_banks=result["rejected_banks"]

    )

    return response