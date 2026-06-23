"""
Notification sender.

Delivery backends, in priority order:
  1. Resend HTTP API   — if RESEND_API_KEY is set.
  2. SMTP              — if SMTP_HOST + SMTP_USER + SMTP_PASS are set.
  3. Console log       — always, so dev workflows still see the content.

Every notification is persisted to the notifications table (with a `delivered`
flag) so the owner can audit them regardless of backend.

Web push is intentionally deferred to STEP 4 (it needs the PWA service worker).
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
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or "noreply@sage.school")
SCHOOL_NAME = "Sage"


def _send_via_resend(to_email: str, subject: str, body: str) -> bool:
    """POST to the Resend HTTP API. Returns True on a 2xx response."""
    try:
        import httpx
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": f"{SCHOOL_NAME} <{FROM_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "text": body,
                "html": _html_wrap(subject, body),
            },
            timeout=15,
        )
        if resp.status_code // 100 == 2:
            return True
        print(f"[notifications] Resend failed {resp.status_code}: {resp.text}",
              file=sys.stderr)
        return False
    except Exception as e:  # noqa: BLE001
        print(f"[notifications] Resend send error: {e}", file=sys.stderr)
        return False


def _send_via_smtp(to_email: str, subject: str, body: str) -> bool:
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
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[notifications] SMTP send failed: {e}", file=sys.stderr)
        return False


def send(db: Session, to_email: str, subject: str, body: str, kind: str = "email") -> bool:
    """Send (best effort) + persist. Returns True if at least logged."""
    delivered = False
    if to_email:
        if RESEND_API_KEY:
            delivered = _send_via_resend(to_email, subject, body)
        elif SMTP_HOST and SMTP_USER and SMTP_PASS:
            delivered = _send_via_smtp(to_email, subject, body)

    bar = "═" * 60
    print(f"\n{bar}\n📧  {subject}\n   to: {to_email}\n{bar}\n{body}\n{bar}\n")

    db.add(models.Notification(
        to_email=to_email or "", subject=subject, body=body,
        kind=kind, delivered=delivered,
    ))
    db.commit()
    return True


def recipients_for_student(db: Session, student: models.Student) -> list[str]:
    """The student's own login email + every approved parent's email (deduped)."""
    emails: list[str] = []
    if student.user_id:
        u = db.query(models.User).filter(models.User.id == student.user_id).first()
        if u and u.email:
            emails.append(u.email)
    links = db.query(models.ParentLink).filter(
        models.ParentLink.student_id == student.id,
        models.ParentLink.status == "approved",
    ).all()
    for l in links:
        pu = db.query(models.User).filter(models.User.id == l.parent_user_id).first()
        if pu and pu.email:
            emails.append(pu.email)
    # dedupe, preserve order
    seen = set()
    return [e for e in emails if not (e in seen or seen.add(e))]


def notify_student(db: Session, student: models.Student, subject: str, body: str,
                   kind: str = "email") -> int:
    """Send the same message to a student and their approved parents.

    Returns the number of recipients messaged. Never raises — a notification
    failure must not break the underlying action (payment, marks, …).
    """
    try:
        emails = recipients_for_student(db, student)
        for e in emails:
            send(db, e, subject, body, kind=kind)
        return len(emails)
    except Exception as e:  # noqa: BLE001
        print(f"[notifications] notify_student failed: {e}", file=sys.stderr)
        return 0


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
