"""
FlowIQ – Root Entry Point
Run from the project root with:
    uvicorn main:app --reload
"""

# Import the FastAPI `app` object from the backend package.
# The backend/main.py bootstraps sys.path so all internal modules resolve.
from backend.main import app  # noqa: F401  (re-exported for uvicorn)
