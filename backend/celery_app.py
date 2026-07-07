import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from celery import Celery
from celery.schedules import crontab

celery = Celery(
    "emailai",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    beat_schedule={
        "poll-emails-every-60s": {
            "task": "auto_poll_emails",
            "schedule": 60.0,  # every 60 seconds
        },
    },
)


@celery.task(bind=True, name="run_email_agent_task")
def run_email_agent_task(self, email: str, task: str = None):
    """Manually triggered agent task."""
    try:
        from agents.email_agent import run_email_agent
        result = run_email_agent(email, task)
        return {"status": "done", "result": result}
    except Exception as exc:
        self.retry(exc=exc, countdown=10, max_retries=2)


@celery.task(name="auto_poll_emails")
def auto_poll_emails():
    """
    Celery Beat task — runs every 60 seconds.
    Checks all linked email accounts for new unread emails and auto-replies.
    Already-replied messages are tracked in Postgres (replied_messages table)
    and are also re-checked atomically inside agent.send_reply, so a message
    can never be replied to twice even if polls overlap.
    """
    from agents.email_agent import run_email_agent
    from db import get_session, GmailToken, is_already_replied

    session = get_session()
    try:
        linked_emails = [row.email for row in session.query(GmailToken.email)]
    finally:
        session.close()

    if not linked_emails:
        return {"status": "no linked accounts"}

    results = []
    for email in linked_emails:
        try:
            from auth.oauth import build_gmail_service

            service = build_gmail_service(email)
            result = service.users().messages().list(
                userId="me", maxResults=10, q="is:unread in:inbox"
            ).execute()
            messages = result.get("messages", [])

            # Filter out already replied messages
            new_ids = [m["id"] for m in messages if not is_already_replied(m["id"])]

            if not new_ids:
                results.append({"email": email, "status": "no new emails"})
                continue

            agent_result = run_email_agent(
                email,
                task=(
                    f"Check unread emails in {email}'s inbox. "
                    f"Focus only on these message IDs: {new_ids}. "
                    "For each real personal or business email (not newsletters), "
                    "read the full content including all PDF attachments, "
                    "understand the context, and send a relevant professional reply."
                )
            )

            results.append({"email": email, "status": "done", "result": agent_result})

        except Exception as e:
            results.append({"email": email, "status": "error", "error": str(e)})

    return results
