"""
Audit middleware — captures every state-changing request.

Decodes the JWT directly so we don't depend on FastAPI's auth chain.
Failures here never block the request.
"""

import re
from starlette.middleware.base import BaseHTTPMiddleware

import auth
import models
from database import SessionLocal


# Friendly summaries for common (METHOD, PATH_PATTERN) combos.
_SUMMARIES = [
    (r"POST",   r"^/auth/login$",                 "Sign in"),
    (r"POST",   r"^/auth/signup$",                "Sign up"),
    (r"POST",   r"^/auth/forgot$",                "Requested password reset"),
    (r"POST",   r"^/auth/reset$",                 "Reset password"),
    (r"PUT",    r"^/auth/me/password$",           "Changed password"),
    (r"PUT",    r"^/auth/me$",                    "Updated profile"),
    (r"POST",   r"^/auth/users/\d+/approve$",     "Approved user"),
    (r"DELETE", r"^/auth/users/\d+$",             "Deleted user"),
    (r"POST",   r"^/parent/claim$",               "Parent claimed child"),
    (r"POST",   r"^/parent/links/\d+/approve$",   "Approved parent link"),
    (r"POST",   r"^/parent/links/\d+/reject$",    "Rejected parent link"),
    (r"POST",   r"^/students$",                   "Added student"),
    (r"PUT",    r"^/students/\d+$",               "Updated student"),
    (r"DELETE", r"^/students/\d+$",               "Deleted student"),
    (r"POST",   r"^/students/import$",            "Imported students CSV"),
    (r"POST",   r"^/teachers$",                   "Added teacher"),
    (r"PUT",    r"^/teachers/\d+$",               "Updated teacher"),
    (r"DELETE", r"^/teachers/\d+$",               "Deleted teacher"),
    (r"POST",   r"^/payments$",                   "Recorded payment"),
    (r"POST",   r"^/payments/razorpay/verify$",   "Recorded online payment"),
    (r"POST",   r"^/expenses$",                   "Recorded expense"),
    (r"DELETE", r"^/expenses/\d+$",               "Deleted expense"),
    (r"POST",   r"^/fee-structures$",             "Created fee structure"),
    (r"POST",   r"^/fee-structures/\d+/apply$",   "Applied fee structure"),
    (r"POST",   r"^/attendance/mark$",            "Marked attendance"),
    (r"POST",   r"^/timetable$",                  "Added timetable slot"),
    (r"PUT",    r"^/timetable/\d+$",              "Updated timetable slot"),
    (r"DELETE", r"^/timetable/\d+$",              "Deleted timetable slot"),
    (r"POST",   r"^/exams$",                      "Created exam"),
    (r"POST",   r"^/exams/\d+/marks/bulk$",       "Saved exam marks"),
    (r"DELETE", r"^/exams/\d+$",                  "Deleted exam"),
    (r"POST",   r"^/assignments$",                "Created assignment"),
    (r"POST",   r"^/student/me/assignments/\d+/submit$", "Submitted assignment"),
    (r"POST",   r"^/assignments/submissions/\d+/grade$", "Graded submission"),
    (r"PUT",    r"^/assignments/\d+$",            "Updated assignment"),
    (r"DELETE", r"^/assignments/\d+$",            "Deleted assignment"),
    (r"POST",   r"^/tiles$",                      "Added tile"),
    (r"PUT",    r"^/tiles/\d+$",                  "Updated tile"),
    (r"DELETE", r"^/tiles/\d+$",                  "Deleted tile"),
    (r"PUT",    r"^/finance/accounts/\w+$",       "Updated opening balance"),
    (r"POST",   r"^/ai/execute$",                 "Executed AI actions"),
    (r"POST",   r"^/scanner/run$",                "Ran scanner"),
]


def _summarize(method: str, path: str) -> str:
    for m, pat, txt in _SUMMARIES:
        if method == m and re.match(pat, path):
            return txt
    return f"{method} {path}"


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        try:
            method = request.method.upper()
            if method not in ("POST", "PUT", "DELETE", "PATCH"):
                return response
            path = request.url.path
            # Skip noisy / idempotent endpoints
            if path in ("/", "/health"):
                return response

            # Best-effort user resolution from JWT
            user_id = None; user_name = None; user_role = None
            authz = request.headers.get("authorization") or ""
            if authz.lower().startswith("bearer "):
                payload = auth.decode_token(authz.split(" ", 1)[1])
                if payload and "sub" in payload:
                    db = SessionLocal()
                    try:
                        u = db.query(models.User).filter(
                            models.User.id == int(payload["sub"])
                        ).first()
                        if u:
                            user_id = u.id; user_name = u.name; user_role = u.role
                    finally:
                        db.close()

            ip = request.client.host if request.client else None

            db = SessionLocal()
            try:
                row = models.AuditLog(
                    user_id=user_id, user_name=user_name, user_role=user_role,
                    method=method, path=path,
                    status_code=getattr(response, "status_code", None),
                    summary=_summarize(method, path),
                    ip=ip,
                )
                db.add(row); db.commit()
            finally:
                db.close()
        except Exception:
            # Never let audit break the request.
            pass
        return response
