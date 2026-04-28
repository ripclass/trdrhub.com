"""Minimal SMTP email helper — Phase A2 closure.

Lifted from BankNotificationService._send_email so other parts of the
app (re-papering invitations, A3 notifications, etc.) can fire email
without taking on the bank service's dependencies.

Reads the same env vars BankNotificationService already documents:
  SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
  SMTP_FROM_EMAIL, SMTP_USE_TLS

When SMTP_HOST is unset, returns False without raising — the caller
treats the email as "skipped" and continues. This keeps local dev +
test runs from needing real SMTP credentials.
"""

from __future__ import annotations

import logging
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


def _html_to_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    import html as html_lib

    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def send_email(
    *,
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    from_email: Optional[str] = None,
) -> bool:
    """Send a single email via SMTP. Returns True on send, False if
    skipped (no SMTP config) or on error (logged, never raised).

    Caller treats the return value as informational — don't block
    business logic on email delivery.
    """
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        logger.info("send_email skipped — SMTP_HOST not configured (to=%s)", to)
        return False

    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = (
        from_email
        or os.getenv("SMTP_FROM_EMAIL")
        or "noreply@trdrhub.com"
    )
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to

    msg.attach(MIMEText(text_body or _html_to_text(html_body), "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_use_tls:
                server.starttls()
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            server.send_message(msg)
        logger.info("send_email delivered to %s (subject=%r)", to, subject)
        return True
    except Exception:
        logger.exception("send_email failed (to=%s)", to)
        return False


__all__ = ["send_email"]
