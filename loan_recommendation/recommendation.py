from fastapi import APIRouter, HTTPException

from loan_recommendation.schemas import (
    LoanRecommendationRequest,
    LoanRecommendationResponse,
    RecommendedBank,
)
from loan_recommendation.services import RecommendationService


router = APIRouter(
    prefix="/loan-recommendation",
    tags=["Loan Recommendation"]
)

recommendation_service = RecommendationService()

@router.post(
    "/recommend",
    response_model=LoanRecommendationResponse
)
def recommend_loan(request: LoanRecommendationRequest):

    print(">>> Endpoint reached")

    recommendations = recommendation_service.recommend(request)

    print(">>> Recommendation service completed")

    response = LoanRecommendationResponse(
        recommendations=[
            RecommendedBank(**bank)
            for bank in recommendations
        ]
    )

    print(">>> Returning response")

    return response