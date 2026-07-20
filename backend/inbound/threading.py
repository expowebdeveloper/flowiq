"""
RFC 2822 email threading (In-Reply-To / References), as distinct from Gmail's
own threadId concept.

Gmail groups messages within ONE mailbox by threadId regardless of headers,
so a sender's own Sent/Inbox view threads correctly even if In-Reply-To is
wrong. But every other mail client — including the RECIPIENT's Gmail, since
that's a different mailbox/account — threads primarily by chasing the
In-Reply-To/References header chain back through real RFC Message-Id values.
Setting those headers to a Gmail API message id (e.g. "19f6f73047ef45db")
instead of the actual "Message-Id" header value (e.g.
"<CAKn...@mail.gmail.com>") looks fine in the sender's own mailbox but
silently breaks threading for the recipient, since that id matches nothing.
"""


def get_message_id_header(service, message_id: str, user_id: str = "me") -> str | None:
    """
    Fetches the real RFC "Message-Id" header for a Gmail API message id, for
    use in a reply's In-Reply-To/References headers. Returns None if the
    message/header can't be found (caller should just omit threading headers
    rather than send a reply with a broken thread reference).
    """
    try:
        msg = (
            service.users()
            .messages()
            .get(userId=user_id, id=message_id, format="metadata", metadataHeaders=["Message-Id", "References"])
            .execute()
        )
    except Exception:
        return None
    return _header_value(msg, "Message-Id")


def build_references_header(service, message_id: str, user_id: str = "me") -> str | None:
    """
    Builds the References header value for a reply to `message_id`: the
    original message's own References chain (if it had one, i.e. it was
    itself a reply) with its Message-Id appended — per RFC 2822/5322, which
    the reply chains back through. Falls back to just that Message-Id when
    the original message wasn't part of a prior chain.
    """
    try:
        msg = (
            service.users()
            .messages()
            .get(userId=user_id, id=message_id, format="metadata", metadataHeaders=["Message-Id", "References"])
            .execute()
        )
    except Exception:
        return None

    msg_id_header = _header_value(msg, "Message-Id")
    if not msg_id_header:
        return None

    prior_references = _header_value(msg, "References")
    if prior_references:
        return f"{prior_references} {msg_id_header}"
    return msg_id_header


def apply_threading_headers(mime, service, in_reply_to_gmail_message_id: str, user_id: str = "me") -> None:
    """
    Sets In-Reply-To/References on an outgoing email.MIMEMultipart/MIMEText
    object so it threads correctly in the RECIPIENT's mailbox, not just the
    sender's own (which Gmail threads by threadId regardless of headers).
    in_reply_to_gmail_message_id is the Gmail API id (the short hex string,
    e.g. from a webhook payload or messages.list) of the message being
    replied to — this looks up its real Message-Id header rather than using
    that id directly, which is not a valid RFC Message-Id and would leave
    the recipient's client unable to chain the reply.
    """
    message_id_header = get_message_id_header(service, in_reply_to_gmail_message_id, user_id)
    if not message_id_header:
        return
    mime["In-Reply-To"] = message_id_header
    references = build_references_header(service, in_reply_to_gmail_message_id, user_id) or message_id_header
    mime["References"] = references


def _header_value(msg: dict, name: str) -> str | None:
    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value")
    return None
