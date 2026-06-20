"""
Notification helper — sends email or logs locally.

If SMTP_HOST + SMTP_USER + SMTP_PASS env vars are set, sends real email
via smtplib. Otherwise prints to the server console and persists the
notification in the DB so Owner can audit it.
"""

import os
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

import models

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or "noreply@nagarjuna.school")
SCHOOL_NAME = "Nagarjuna High School"


def send(db: Session, to_email: str, subject: str, body: str, kind: str = "email") -> bool:
    """
    Always returns True if the notification was at least logged. Persists to
    the notifications table either way.
    """
    delivered = False

    # Try SMTP
    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = f"{SCHOOL_NAME} <{FROM_EMAIL}>"
            msg["To"]      = to_email
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(_html_wrap(subject, body), "html"))
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as srv:
                srv.starttls()
                srv.login(SMTP_USER, SMTP_PASS)
                srv.sendmail(FROM_EMAIL, [to_email], msg.as_string())
            delivered = True
        except Exception as e:
            print(f"[notifications] SMTP send failed: {e}", file=sys.stderr)
            delivered = False

    # Always log to console + DB so dev workflows still see the content.
    bar = "═" * 60
    print(f"\n{bar}\n📧  {subject}\n   to: {to_email}\n{bar}\n{body}\n{bar}\n")

    n = models.Notification(
        to_email=to_email, subject=subject, body=body,
        kind=kind, delivered=delivered,
    )
    db.add(n)
    db.commit()
    return True


def _html_wrap(subject: str, body: str) -> str:
    safe_body = body.replace("\n", "<br/>")
    return f"""
<!DOCTYPE html><html><body style="font-family:-apple-system,Segoe UI,Arial,sans-serif;
  background:#f6f4ee; color:#2a2520; padding:24px;">
  <div style="max-width:560px; margin:0 auto; background:#fff;
    border-radius:12px; padding:28px; box-shadow:0 8px 24px rgba(0,0,0,.06);">
    <h2 style="margin:0 0 6px; color:#a8763d;">{SCHOOL_NAME}</h2>
    <h3 style="margin:0 0 18px; font-weight:600;">{subject}</h3>
    <div style="line-height:1.55; color:#3d342b;">{safe_body}</div>
  </div>
</body></html>
"""
