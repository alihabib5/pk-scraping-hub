"""Post-scrape notification: email the run's Excel to RECIPIENT_EMAILS via the
AWS SES SMTP interface, with the download link in the body.

Everything here is best-effort — a notification failure never affects a scrape.
Nothing is sent unless RECIPIENT_EMAILS and the SES credentials are set.
"""

import logging
import smtplib
import threading
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.core import exports, run_manager

logger = logging.getLogger(__name__)


def _recipients() -> list[str]:
    return [e.strip() for e in (settings.recipient_emails or "").split(",") if e.strip()]


def _send_email(recipients: list[str], subject: str, body_html: str, attachment: bytes, filename: str) -> bool:
    """Send an HTML email with the Excel attached, via the AWS SES SMTP interface."""
    sender = settings.aws_ses_from_email
    username = settings.aws_ses_username
    password = settings.aws_ses_password
    region = settings.aws_region or "us-east-1"
    host = f"email-smtp.{region}.amazonaws.com"
    port = 587

    if not all([sender, username, password]):
        logger.warning("AWS SES SMTP credentials incomplete — skipping email notification")
        return False

    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(body_html, "html"))

        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)

        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls()
            server.login(username, password)
            server.sendmail(sender, recipients, msg.as_bytes())

        logger.info("Email sent via SES SMTP to %s", recipients)
        return True
    except Exception as exc:  # noqa: BLE001 — email is best-effort
        logger.error("SES SMTP email failed: %s", exc)
        return False


def _notify(run_id: str, scraper: str, record_count: int) -> None:
    recipients = _recipients()
    if not recipients:
        logger.info("RECIPIENT_EMAILS not configured — skipping notification for %s", run_id)
        return

    run = run_manager.get_run(run_id)
    if not run:
        return

    payload = exports.excel_bytes(run)
    if not payload:
        logger.warning("run %s has nothing to attach — skipping notification", run_id)
        return
    data, filename = payload

    now = datetime.now()
    hr = now.strftime("%I").lstrip("0") or "12"
    ts = now.strftime(f"%Y-%m-%d, {hr}:%M %p")
    download_url = f"{settings.public_base_url.rstrip('/')}/runs/{run_id}/download"

    subject = f"{scraper.upper()} Scrape Complete — {record_count} records ({ts})"
    body_html = f"""\
<html><body>
<p>The <strong>{scraper.upper()}</strong> scraper has finished.</p>
<ul>
  <li><strong>Run ID:</strong> {run_id}</li>
  <li><strong>Records scraped:</strong> {record_count}</li>
  <li><strong>Completed at:</strong> {ts}</li>
</ul>
<p>The Excel report is attached.</p>
<p><a href="{download_url}">Download it again from PK-Hub</a></p>
</body></html>"""

    _send_email(recipients, subject, body_html, data, filename)


def notify_scrape_completion(run_id: str, scraper: str, record_count: int) -> None:
    """Fire a completion notification in a background thread (best-effort).

    Returns immediately and never raises, so email latency or failure can't
    affect the scrape.
    """
    threading.Thread(
        target=_notify, args=(run_id, scraper, record_count), daemon=True
    ).start()
