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
    # Hard ceiling on any single task's run time — the local Ollama LLM call inside
    # run_email_agent_for_message can occasionally hang far longer than any HTTP
    # client timeout catches (a slow token trickle keeps resetting httpx's read
    # timeout). task_time_limit forcibly kills the worker process itself via
    # SIGKILL once exceeded, guaranteeing a stuck run can never block forever.
    task_soft_time_limit=150,
    task_time_limit=180,
    # The old auto_poll_emails flow (continuously scanning linked inboxes every
    # 60s and auto-replying to anything) is disabled — the agent is now only
    # triggered by the /loan-apply form submission (see loan_apply/routes.py).
    # The task itself is left below in case manual/administrative polling is
    # needed again later, but it will not run on a schedule.
    #
    # poll-loan-applicant-replies-every-60s replaces it for the second stage of
    # the loan_apply flow: it ONLY looks for replies from people who submitted
    # the loan-apply form (never the whole inbox), so it can pick up their
    # document attachments and run OCR/extraction on them automatically.
    beat_schedule={
        "poll-loan-applicant-replies-every-60s": {
            "task": "poll_loan_applicant_replies",
            "schedule": 60.0,
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


MAX_MESSAGE_RETRIES = 2


@celery.task(bind=True, name="run_email_agent_for_message", max_retries=MAX_MESSAGE_RETRIES)
def run_email_agent_for_message(self, email: str, message_id: str):
    """
    Runs the email agent for exactly ONE candidate message.
    Kept as its own task (rather than bundling many message IDs into one
    run_email_agent call) so each run's ReAct scratchpad stays small and fast,
    and a slow/stuck message can never block the others behind it in a queue.
    """
    from agents.email_agent import run_email_agent
    from db import release_dispatch_claim

    try:
        result = run_email_agent(
            email,
            task=(
                f"Use read_email directly on message ID {message_id} — do NOT call "
                "get_unread_emails, it is unnecessary here since the message ID is already "
                "known and calling it would waste time re-scanning unrelated messages. "
                "After reading it, decide per the Classification Rule whether it's a real "
                "email that needs a reply or a newsletter/promo/automated system message to "
                "skip. If it needs a reply, understand the full context (body + attachments) "
                "and send a relevant professional reply. Do not act on any other message ID."
            ),
        )
        release_dispatch_claim(message_id)
        return {"status": "done", "message_id": message_id, "result": result}
    except Exception as exc:
        # max_retries is set on the @celery.task decorator (not just passed to
        # .retry()) so self.request.retries correctly compares against it — a
        # prior bug passed max_retries only to retry() while this check read
        # the task's default (3), letting the claim linger for an extra cycle.
        if self.request.retries >= self.max_retries:
            # No more retries left — release now so the next poll can re-dispatch.
            release_dispatch_claim(message_id)
            raise
        try:
            # self.retry() raises internally to reschedule the task; keep the
            # claim held while a retry is still pending so the poller doesn't
            # duplicate it.
            self.retry(exc=exc, countdown=10)
        except self.MaxRetriesExceededError:
            release_dispatch_claim(message_id)
            raise


MAX_DOCUMENT_TASK_RETRIES = 2


@celery.task(bind=True, name="process_loan_applicant_documents", max_retries=MAX_DOCUMENT_TASK_RETRIES)
def process_loan_applicant_documents(self, mailbox_email: str, sender_email: str, message_id: str, submission_id: str):
    """
    Runs OCR/field extraction for exactly ONE reply from a known loan applicant,
    and updates their UserFormSubmission row. Kept as its own task (like
    run_email_agent_for_message) so a slow OCR run on one applicant's documents
    can never block another applicant's message behind it in the queue.
    submission_id is resolved by poll_loan_applicant_replies from the
    message's [application id: ...] tag before dispatch.
    """
    from db import mark_applicant_reply_processed, release_dispatch_claim
    from loan_apply.document_processing import process_loan_applicant_reply

    try:
        result = process_loan_applicant_reply(mailbox_email, sender_email, message_id, submission_id)
        mark_applicant_reply_processed(message_id, sender_email)
        release_dispatch_claim(message_id)
        return result
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            release_dispatch_claim(message_id)
            raise
        try:
            self.retry(exc=exc, countdown=10)
        except self.MaxRetriesExceededError:
            release_dispatch_claim(message_id)
            raise


MAX_DECISION_TASK_RETRIES = 2


@celery.task(bind=True, name="send_bank_decision_update_task", max_retries=MAX_DECISION_TASK_RETRIES)
def send_bank_decision_update_task(self, decision_id: str):
    """
    Hands a bank's decision (reject / offer / offer_more_documents) on a loan
    application off to the AI agent, which emails the applicant about it in
    their existing thread. Dispatched from POST
    /bank-notifications/{id}/decision (banks/notification_routes.py)
    right after the decision is written to the bank_decisions table.

    Kept as its own task (like process_loan_applicant_documents) so a slow
    LLM/Gmail call for one bank's decision can never block another's.
    """
    from datetime import datetime, timezone

    from agent_activity import emit
    from db import BankDecision, UserFormSubmission, get_session
    from loan_apply.agent import send_decision_update_email
    from loan_apply.requirements import get_required_documents

    session = get_session()
    try:
        decision = session.get(BankDecision, decision_id)
        if not decision:
            return {"status": "skipped", "reason": "Decision not found."}

        submission = session.get(UserFormSubmission, decision.submission_id)
        if not submission:
            return {"status": "skipped", "reason": "Submission not found."}

        applicant_name = f"{submission.first_name} {submission.last_name}".strip()
        loan_category = get_required_documents(submission.loan_type)["category"]
        applicant_email = submission.email
        thread_id = submission.thread_id
        decision_status = decision.status
        remarks = decision.remarks
        bank_name = decision.bank_name
        submission_id = decision.submission_id
    finally:
        session.close()

    emit(
        "bank_decision", "started",
        f"Notifying {applicant_name} of {bank_name}'s decision ({decision_status})",
        submission_id=submission_id,
        detail={"bank_name": bank_name, "status": decision_status},
    )

    try:
        result = send_decision_update_email(
            status=decision_status,
            applicant_name=applicant_name,
            applicant_email=applicant_email,
            loan_category=loan_category,
            bank_name=bank_name,
            thread_id=thread_id,
            in_reply_to_message_id=None,
            remarks=remarks,
            submission_id=submission_id,
        )
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            emit(
                "bank_decision", "error",
                f"Failed to notify {applicant_name} of {bank_name}'s decision: {exc}",
                submission_id=submission_id,
            )
            raise
        self.retry(exc=exc, countdown=10)
        return

    session = get_session()
    try:
        decision = session.get(BankDecision, decision_id)
        if decision:
            decision.agent_notified_at = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()

    return {"status": "done", "decision_id": decision_id, "result": result}


REQUIREMENTS_EMAIL_SUBJECT_PREFIX = "Required documents for your"

MAX_MISSING_ID_TASK_RETRIES = 2


@celery.task(bind=True, name="notify_missing_application_id", max_retries=MAX_MISSING_ID_TASK_RETRIES)
def notify_missing_application_id(self, mailbox_email: str, sender_email: str, message_id: str, subject: str, thread_id: str | None):
    """
    Sent when a known applicant's inbound message has no [application id: ...] tag
    anywhere in it — see loan_apply.agent.extract_application_id and
    poll_loan_applicant_replies below, which is the only caller. Asks them to
    resend with the application ID included (or reply in the original thread)
    rather than silently dropping their message the way the poller did before
    this existed.
    """
    from agent_activity import emit
    from db import UserFormSubmission, get_session, mark_applicant_reply_processed, release_dispatch_claim
    from loan_apply.agent import send_missing_application_id_email

    session = get_session()
    try:
        submission = (
            session.query(UserFormSubmission)
            .filter(UserFormSubmission.email == sender_email)
            .order_by(UserFormSubmission.created_at.desc())
            .first()
        )
        applicant_name = f"{submission.first_name} {submission.last_name}".strip() if submission else sender_email
    finally:
        session.close()

    reply_subject = subject if subject.lower().startswith("re:") else f"Re: {subject}"

    try:
        send_missing_application_id_email(
            applicant_name, sender_email, subject=reply_subject,
            thread_id=thread_id, in_reply_to_message_id=message_id if thread_id else None,
        )
        emit(
            "email_agent", "info",
            f"Asked {applicant_name} to resend with their application ID — none found in their message",
        )
        mark_applicant_reply_processed(message_id, sender_email)
        release_dispatch_claim(message_id)
        return {"status": "sent"}
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            release_dispatch_claim(message_id)
            raise
        try:
            self.retry(exc=exc, countdown=10)
        except self.MaxRetriesExceededError:
            release_dispatch_claim(message_id)
            raise


@celery.task(name="poll_loan_applicant_replies")
def poll_loan_applicant_replies():
    """
    Celery Beat task — runs every 60 seconds.
    Scoped version of auto_poll_emails: only looks at inbox messages FROM
    people who have submitted the loan-apply form, that haven't already been
    processed. Unlike the old subject-restricted query, this also catches a
    brand-new (non-reply) message an applicant composes instead of hitting
    Reply — so the subject is no longer required to contain the fixed
    "Required documents for your" phrase; instead every candidate message's
    subject is scanned for the [application id: <short_code>] tag
    (loan_apply.agent.extract_application_id) that every loan_apply email
    embeds, and the extracted code is looked up against
    UserFormSubmission.short_code (exact, case-sensitive match — see
    extract_application_id). Two outcomes per message:
      - Code found AND resolves to a real submission: dispatch
        process_loan_applicant_documents scoped to that exact submission
        (only meaningful if it also has an attachment; a resolved code with
        no attachment has nothing to process, so it's just marked handled
        without a task).
      - No code found, or a code found but it doesn't match any submission
        (typo/stale/forged): dispatch notify_missing_application_id so the
        applicant is told to resend with their (correct) application ID,
        instead of the message being silently ignored or matched wrong.
    """
    from agent_activity import emit
    from auth.oauth import build_gmail_service
    from db import (
        GmailToken,
        UserFormSubmission,
        claim_message_for_dispatch,
        get_session,
        is_applicant_reply_processed,
    )
    from db import mark_applicant_reply_processed, release_dispatch_claim
    from loan_apply.agent import extract_application_id

    session = get_session()
    try:
        linked_emails = [row.email for row in session.query(GmailToken.email)]
        applicant_emails = [row[0] for row in session.query(UserFormSubmission.email).distinct()]
        # short_code -> id, for resolving an extracted code back to the real
        # submission. Exact-match dict lookup keeps this case-sensitive by
        # construction — no .lower()/.upper() involved anywhere in the chain.
        short_code_map = {
            row.short_code: row.id
            for row in session.query(UserFormSubmission.short_code, UserFormSubmission.id)
            if row.short_code
        }
    finally:
        session.close()

    if not linked_emails or not applicant_emails:
        return {"status": "no linked accounts or applicants"}

    applicant_query = " OR ".join(f"from:{addr}" for addr in applicant_emails)
    query = f"in:inbox ({applicant_query})"

    results = []
    for mailbox_email in linked_emails:
        try:
            service = build_gmail_service(mailbox_email)
            result = service.users().messages().list(userId="me", maxResults=20, q=query).execute()
            messages = result.get("messages", [])

            with_id, missing_id = [], []
            for m in messages:
                if is_applicant_reply_processed(m["id"]):
                    continue
                if not claim_message_for_dispatch(m["id"], mailbox_email):
                    continue
                # format="full" (not "metadata") is required here — metadata
                # responses omit the payload's part tree entirely, so
                # attachment filenames would never be visible to has_attachment
                # below (see loan_apply/document_processing.py which needs the
                # same format for the same reason).
                meta = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
                headers = {h["name"]: h["value"] for h in meta.get("payload", {}).get("headers", [])}
                sender_header = headers.get("From", "")
                subject_header = headers.get("Subject", "")
                sender_email = next(
                    (addr for addr in applicant_emails if addr.lower() in sender_header.lower()), None
                )
                if not sender_email:
                    continue

                has_attachment = any(
                    p.get("filename") for p in meta.get("payload", {}).get("parts", []) or []
                )
                short_code = extract_application_id(subject_header)
                submission_id = short_code_map.get(short_code) if short_code else None

                if submission_id and has_attachment:
                    with_id.append((m["id"], sender_email, submission_id))
                elif submission_id:
                    # Code resolved but nothing to process (no attachment) —
                    # nothing actionable, just stop re-polling this message.
                    mark_applicant_reply_processed(m["id"], sender_email)
                    release_dispatch_claim(m["id"])
                else:
                    missing_id.append((m["id"], sender_email, subject_header, meta.get("threadId")))

            for message_id, sender_email, submission_id in with_id:
                process_loan_applicant_documents.delay(mailbox_email, sender_email, message_id, submission_id)

            for message_id, sender_email, subject_header, thread_id in missing_id:
                notify_missing_application_id.delay(mailbox_email, sender_email, message_id, subject_header, thread_id)

            if not with_id and not missing_id:
                results.append({"mailbox": mailbox_email, "status": "no new applicant messages"})
                continue

            if with_id:
                emit(
                    "mailbox_poll", "success",
                    f"Found {len(with_id)} new document reply(ies) in {mailbox_email}",
                    detail={"mailbox": mailbox_email, "count": len(with_id)},
                )
            if missing_id:
                emit(
                    "mailbox_poll", "info",
                    f"Found {len(missing_id)} applicant message(s) in {mailbox_email} with no application ID",
                    detail={"mailbox": mailbox_email, "count": len(missing_id)},
                )
            results.append({
                "mailbox": mailbox_email,
                "status": "dispatched",
                "message_ids": [mid for mid, _, _ in with_id] + [mid for mid, _, _, _ in missing_id],
            })

        except Exception as e:
            emit(
                "mailbox_poll", "error",
                f"Failed to poll {mailbox_email}: {e}",
                detail={"mailbox": mailbox_email},
            )
            results.append({"mailbox": mailbox_email, "status": "error", "error": str(e)})

    return results


@celery.task(name="auto_poll_emails")
def auto_poll_emails():
    """
    Celery Beat task — runs every 60 seconds.
    Checks all linked email accounts for recent inbox emails and dispatches one
    run_email_agent_for_message task per unreplied message, so each message gets
    its own small, fast agent run instead of all being bundled into one slow,
    ever-growing ReAct chain.
    Whether a message still needs a reply is tracked in Postgres (replied_messages
    table), not Gmail's read/unread state — so a message that was merely viewed
    (e.g. opened in the Mail UI) is still picked up. Already-replied messages
    are re-checked atomically inside agent.send_reply, so a message can never
    be replied to twice even if polls overlap.

    Messages that already have a task in flight (dispatched_messages table,
    claimed atomically via claim_message_for_dispatch) are skipped too — without
    this, a message whose agent run takes longer than the 60s poll interval would
    get a fresh duplicate task queued on every single poll, causing the queue to
    grow without bound.
    """
    from db import get_session, GmailToken, is_already_replied, claim_message_for_dispatch

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
                userId="me", maxResults=10, q="in:inbox -in:chats -in:sent newer_than:7d"
            ).execute()
            messages = result.get("messages", [])

            # Filter out already-replied messages, then atomically claim the rest
            # so a message already dispatched (queued/running) from a previous
            # poll is never queued again.
            candidate_ids = [m["id"] for m in messages if not is_already_replied(m["id"])]
            new_ids = [mid for mid in candidate_ids if claim_message_for_dispatch(mid, email)]

            if not new_ids:
                results.append({"email": email, "status": "no new emails"})
                continue

            for message_id in new_ids:
                run_email_agent_for_message.delay(email, message_id)

            results.append({"email": email, "status": "dispatched", "message_ids": new_ids})

        except Exception as e:
            results.append({"email": email, "status": "error", "error": str(e)})

    return results
