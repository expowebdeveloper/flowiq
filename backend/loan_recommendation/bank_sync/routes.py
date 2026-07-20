from fastapi import APIRouter

from loan_recommendation.bank_sync.services import sync_banks

router = APIRouter(
    prefix="/bank-sync",
    tags=["Bank Sync"]
)


@router.post("/sync")
def sync():

    sync_banks()

    return {
        "message": "Banks synchronized successfully."
    }