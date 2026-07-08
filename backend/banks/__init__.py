from .loan_categories import router as loan_categories_router
from .loan_rates import router as loan_rates_router
from .applications import router as loan_applications_router

__all__ = ["loan_categories_router", "loan_rates_router", "loan_applications_router"]
