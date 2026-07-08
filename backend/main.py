from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import oauth_router
from inbound import router as inbound_router
from outbound import router as outbound_router
from agents import router as agents_router
from banks import loan_categories_router, loan_rates_router, loan_applications_router

load_dotenv()

app = FastAPI(title="Email AI - Gmail Inbox Retriever")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(oauth_router)
app.include_router(inbound_router)
app.include_router(outbound_router)
app.include_router(agents_router)
app.include_router(loan_categories_router)
app.include_router(loan_rates_router)
app.include_router(loan_applications_router)


@app.get("/", tags=["utility"])
def root():
    return {
        "service": "Email AI - Gmail Inbox Retriever",
        "endpoints": {
            "1. Link email (OAuth)": "GET /auth/link?email=you@gmail.com",
            "2. Check auth status": "GET /auth/status?email=you@gmail.com",
            "3. List inbox (fast)": "GET /inbox?email=you@gmail.com&max_results=20",
            "4. Get single email + attachments": "GET /inbox/message/{id}?email=you@gmail.com",
            "5. Full inbox with bodies": "GET /inbox/full?email=you@gmail.com&max_results=10",
            "6. Download attachment": "GET /attachments/{email}/{filename}",
            "docs": "/docs",
        }
    }
