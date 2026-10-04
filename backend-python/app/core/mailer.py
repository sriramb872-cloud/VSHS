# backend-python/app/core/mailer.py
"""Plain-SMTP mail delivery for the password-reset OTP.

Deliberately dependency-free (``smtplib`` + ``email.message``) so it works with
any provider that speaks SMTP: Gmail with an app password, Brevo, Resend,
Mailgun, SES, a school's own relay - only the ``SMTP_*`` / ``MAIL_FROM``
environment variables change.

SECURITY INVARIANTS
-------------------
* The OTP is written into the message body and nowhere else: this module never
  logs, raises or returns message content. Log lines carry the recipient domain
  at most, never the body, subject-with-code, or credentials.
* A delivery failure is reported as ``False`` - it never raises into the
  request, so an SMTP outage cannot turn a password reset into a 500.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("scholaris.mail")


def smtp_configured() -> bool:
    """True when outbound mail can be attempted (host + sender + credentials)."""
    return bool(settings.SMTP_HOST and settings.MAIL_FROM)


def _recipient_domain(address: str) -> str:
    """Only the domain is ever attached to a log line."""
    try:
        return address.rsplit("@", 1)[1].lower()
    except IndexError:
        return "unknown"


def send_mail(
    *,
    to: Optional[str],
    subject: str,
    body: str,
    html: Optional[str] = None,
) -> bool:
    """Send one message. Returns True only when the provider accepted it.

    The caller decides what a ``False`` means (the password-reset flow falls
    back to an admin-assisted request so the account is never stranded).
    """
    if not to:
        logger.warning("mail skipped: no recipient configured")
        return False
    if not smtp_configured():
        logger.error(
            "mail delivery failed: SMTP is not configured "
            "(set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, MAIL_FROM)"
        )
        return False

    message = EmailMessage()
    message["From"] = settings.MAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    if html:
        message.add_alternative(html, subtype="html")

    port = int(settings.SMTP_PORT or 587)
    try:
        if port == 465:
            with smtplib.SMTP_SSL(
                settings.SMTP_HOST, port, context=ssl.create_default_context(), timeout=20
            ) as connection:
                if settings.SMTP_USER:
                    connection.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
                connection.send_message(message)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, port, timeout=20) as connection:
                # 25 is plain relay (common on internal relays); everything
                # else gets opportunistic STARTTLS first.
                if port != 25:
                    connection.starttls(context=ssl.create_default_context())
                if settings.SMTP_USER:
                    connection.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
                connection.send_message(message)
    except Exception:  # noqa: BLE001 - any driver error means "not delivered"
        # ``exc_info`` carries the SMTP dialogue only - never the message body,
        # so the OTP cannot leak into the logs even here.
        logger.exception("mail delivery failed for domain %s", _recipient_domain(to))
        return False

    logger.info("mail delivered to domain %s", _recipient_domain(to))
    return True
