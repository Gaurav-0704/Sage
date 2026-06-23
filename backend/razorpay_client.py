"""
Razorpay integration (TIER 2) — thin, SDK-free.

Order creation uses the REST API over httpx; signature verification is a local
HMAC-SHA256 check. Keys come from env (RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET);
test-mode keys (rzp_test_…) work as-is. If keys are absent the feature reports
itself disabled so the UI can hide the "Pay online" option and the manual
payment path keeps working.
"""

import hashlib
import hmac
import os

KEY_ID = os.getenv("RAZORPAY_KEY_ID")
KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

_API = "https://api.razorpay.com/v1/orders"


def enabled() -> bool:
    return bool(KEY_ID and KEY_SECRET)


def create_order(amount_rupees: float, receipt: str, notes: dict | None = None) -> dict:
    """Create a Razorpay order. amount is in rupees; Razorpay wants paise.
    Raises RuntimeError if not configured or the API call fails."""
    if not enabled():
        raise RuntimeError("Online payment is not configured.")
    import httpx
    payload = {
        "amount": int(round(amount_rupees * 100)),   # paise
        "currency": "INR",
        "receipt": receipt,
        "notes": notes or {},
    }
    resp = httpx.post(_API, json=payload, auth=(KEY_ID, KEY_SECRET), timeout=20)
    if resp.status_code // 100 != 2:
        raise RuntimeError(f"Razorpay order failed: {resp.status_code} {resp.text}")
    return resp.json()


def verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify the checkout callback signature: HMAC_SHA256(order_id|payment_id)."""
    if not KEY_SECRET:
        return False
    expected = hmac.new(
        KEY_SECRET.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")
