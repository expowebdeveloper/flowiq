# EmailAI Backend

An AI agent that connects to a broker's Gmail inbox, reads incoming emails (including PDF/image
attachments), and automatically replies — with a built-in loan-inquiry flow that verifies a
client's Aadhaar card before sharing a bank's required-documents checklist.

## Project layout

```
backend/
  main.py              FastAPI app entrypoint — creates the app, wires up all routers
  db.py                SQLAlchemy models + session helpers (Postgres)
  celery_app.py        Background job runner (manual trigger + 60s auto-poll)

  auth/
    jwt.py             JWT issuing/verification, password hashing, route dependencies
    oauth.py           Google OAuth2 flow, Gmail credential storage, /auth/* routes

  inbound/
    extraction.py      Decodes Gmail message bodies, downloads/extracts attachments
    routes.py          Read-only inbox endpoints (/inbox, /inbox/message, /attachments)

  outbound/
    routes.py          /send — compose or reply to an email via Gmail API

  agents/
    aadhaar.py         Aadhaar/PAN detection (Verhoeff checksum), PDF + image OCR extraction
    email_agent.py     The LLM (Groq/Llama) + LangChain ReAct agent, tools, and prompt
    routes.py          /agent/run, /agent/status — trigger and poll the agent

  banks/               Broker-managed loan categories, bank interest rates, loan applications
```

### Why it's split this way

- **auth/** — anything about *who is calling* (JWT for the broker's own login) and *how we get
  into their Gmail* (OAuth2 + token storage) lives together, since both gate access to the rest
  of the API.
- **inbound/** — only concerned with *reading* Gmail: listing messages, decoding bodies,
  extracting attachments to disk.
- **outbound/** — only concerned with *sending* Gmail: the one `/send` endpoint used for manual
  replies (the agent has its own internal send path, see below).
- **agents/** — the AI layer. It depends on `auth` (to get a Gmail client) and `inbound`
  (to decode message bodies), but nothing in `auth`/`inbound`/`outbound` depends on `agents` —
  keeping the AI-specific code (LLM client, prompt, Aadhaar heuristics) isolated and swappable.
- **banks/** — a separate business domain (loan rate data entered by brokers, and loan
  applications submitted with documents) that the agent's tools read from, but which doesn't
  itself touch Gmail.

## End-to-end flow

1. **Broker links Gmail** — `GET /auth/link?email=...` starts a Google OAuth consent flow.
   `GET /auth/callback` receives the code, stores the refresh token in Postgres
   (`gmail_tokens` table), creates/looks-up a `User` row, and issues a JWT for the frontend.
2. **Reading the inbox** — once linked, `GET /inbox`, `GET /inbox/message/{id}`, and
   `GET /inbox/full` all build a Gmail API client from the stored token
   (`auth.oauth.build_gmail_service`) and return message metadata/body/attachments.
3. **Running the AI agent** — `POST /agent/run` (or the Celery Beat job that fires every 60s)
   calls `agents.email_agent.run_email_agent(email)`, which:
   - Fetches unread, not-yet-replied emails (`get_unread_emails` tool)
   - Reads each one fully, including PDF text extraction and image OCR for attachments
     (`read_email` tool, backed by `agents/aadhaar.py`)
   - Skips newsletters/no-reply senders
   - If the email looks like a **loan inquiry** (mentions a bank/loan), runs the
     `check_aadhaar_and_get_requirements` tool:
     - Scans attachments for something that looks like a genuine Aadhaar card (Aadhaar/UIDAI
       keyword **and** a 12-digit number that passes the government's Verhoeff checksum;
       explicitly rejects anything that looks like a PAN card instead)
     - If not found: agent replies asking for the Aadhaar card — never confirms eligibility
     - If found: records a `LoanApplication` + `LoanApplicationDocument`, and replies with the
       exact required-documents list for that bank/loan type from `bank_loan_rates`
   - Otherwise, sends a normal contextual reply based on the email body + attachment content
   - Every reply goes through the `send_reply` tool, which atomically claims the message
     (`replied_messages` table) before sending — so the same email is never replied to twice,
     even across overlapping runs — and marks the Gmail message read afterward as a second
     safety net.
4. **Brokers manage their own loan data** — separately from the agent, brokers use the
   `banks/` endpoints to maintain which loan categories they offer, the interest-rate/document
   data per bank, and to submit/track loan applications directly (not just ones created by the
   agent).

## API Reference

All endpoints are prefixed at the app root (no `/api` prefix). Full interactive docs are always
available at `GET /docs` (Swagger UI) once the server is running.

### Auth (`auth/`)

| Method | Path | Description |
|---|---|---|
| GET | `/auth/link?email=` | Start Gmail OAuth flow for an email address |
| GET | `/auth/callback?code=&state=` | OAuth redirect target — stores the Gmail token, issues a JWT |
| GET | `/auth/status?email=` | Check whether an email is currently linked |
| GET | `/auth/me` | Return the current JWT's user id/email/role (`Authorization: Bearer <token>`) |

### Inbound (`inbound/`)

| Method | Path | Description |
|---|---|---|
| GET | `/inbox?email=&max_results=&page_token=&query=` | List inbox messages (metadata only, fast) |
| GET | `/inbox/message/{message_id}?email=&download_attachments=` | Full body + attachments for one message |
| GET | `/inbox/full?email=&max_results=&query=&download_attachments=` | Full body + attachments for many messages in one call |
| GET | `/attachments/{email}/{filename}` | Download a previously extracted attachment |

### Outbound (`outbound/`)

| Method | Path | Description |
|---|---|---|
| POST | `/send` | Send a new email or reply (`email`, `to`, `subject`, `body`, optional `reply_to_message_id`, `thread_id`, `cc`) |

### Agents (`agents/`)

| Method | Path | Description |
|---|---|---|
| POST | `/agent/run` | Trigger the email agent for an account (`email`, optional custom `task`) — runs async via Celery, returns a `task_id` |
| GET | `/agent/status/{task_id}` | Poll the status/result of a triggered agent run |

The agent also runs automatically every 60 seconds via Celery Beat (`auto_poll_emails` in
`celery_app.py`) for every Gmail account that has ever been linked.

### Banks (`banks/`) — broker-only (JWT with `role=broker` required, except where noted)

| Method | Path | Description |
|---|---|---|
| GET | `/broker/loan-categories` | List the current broker's active loan categories |
| POST | `/broker/loan-categories` | Add/reactivate a loan category (`home_loan`, `education_loan`, `personal_loan`, `car_loan`, `gold_loan`) |
| DELETE | `/broker/loan-categories/{category_id}` | Deactivate a loan category |
| POST | `/bank-loan-rates/bank` | Add one bank's rate/requirements entry for a loan type |
| POST | `/bank-loan-rates` | Bulk upsert multiple bank rate entries |
| GET | `/bank-loan-rates?bank_name=&loan_type=` | **Public** — list stored bank rate/requirement data |
| POST | `/loan-applications` | Submit a loan application with supporting documents (multipart form) |
| GET | `/loan-applications` | List the current broker's submitted applications |
| GET | `/loan-applications/{application_id}/documents/{document_id}` | Download a document attached to an application |

### Utility

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service info + quick endpoint reference |
| GET | `/docs` | Swagger UI |

## Running locally

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then fill in client_id, client_secret, GROQ_API_KEY, DATABASE_URL

uvicorn main:app --reload            # API server
celery -A celery_app worker -B       # agent worker + 60s auto-poll scheduler (needs Redis)
```

Required environment variables (`.env`):

| Variable | Purpose |
|---|---|
| `client_id`, `client_secret` | Google OAuth2 credentials for Gmail access |
| `GROQ_API_KEY` | Groq API key powering the email agent's LLM (`llama-3.3-70b-versatile`) |
| `DATABASE_URL` | Postgres connection string |
| `JWT_SECRET` | Secret used to sign broker login tokens (defaults to an insecure dev value) |
