"""
Config Agent — editable app settings + integration status.

The owner can edit the school profile (name/address/phone/academic year) from
the Settings page; these are stored in the `settings` table and used on receipts
and report cards. Secrets (API keys, SMTP/Razorpay) stay in environment
variables — this agent only *reports whether they're configured*, never their
values, and tells the owner which env var to set.
"""

import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from dependencies import get_db, require_owner, require_school_member

router = APIRouter(prefix="/config", tags=["config"])

PROFILE_KEYS = ("school_name", "school_address", "school_phone", "academic_year")
PROFILE_DEFAULTS = {
    "school_name": "Sage Public School",
    "school_address": "123 Education Lane, Knowledge City",
    "school_phone": "+91 99999 00000",
    "academic_year": "2025-26",
}


def get_setting(db: Session, key: str, default: str = "") -> str:
    row = db.query(models.Setting).filter(models.Setting.key == key).first()
    if row and row.value is not None:
        return row.value
    return PROFILE_DEFAULTS.get(key, default)


def _profile(db: Session) -> dict:
    return {k: get_setting(db, k) for k in PROFILE_KEYS}


def _integration_status() -> dict:
    return {
        "ai":       {"configured": bool(os.getenv("ANTHROPIC_API_KEY")), "env": "ANTHROPIC_API_KEY"},
        "email":    {"configured": bool(os.getenv("RESEND_API_KEY") or os.getenv("SMTP_HOST")),
                     "env": "RESEND_API_KEY or SMTP_HOST/SMTP_USER/SMTP_PASS"},
        "payments": {"configured": bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET")),
                     "env": "RAZORPAY_KEY_ID + RAZORPAY_KEY_SECRET"},
    }


@router.get("", response_model=schemas.ConfigOut)
def get_config(db: Session = Depends(get_db),
               _user: models.User = Depends(require_school_member)):
    """School profile + which integrations are configured (no secret values)."""
    return schemas.ConfigOut(profile=_profile(db), integrations=_integration_status())


@router.put("/profile", response_model=schemas.ConfigOut)
def update_profile(payload: schemas.SchoolProfileIn,
                   db: Session = Depends(get_db),
                   _owner: models.User = Depends(require_owner)):
    """Owner edits the school profile. Only known keys are written."""
    data = payload.model_dump(exclude_unset=True)
    for k in PROFILE_KEYS:
        if k in data and data[k] is not None:
            row = db.query(models.Setting).filter(models.Setting.key == k).first()
            if row:
                row.value = data[k]
            else:
                db.add(models.Setting(key=k, value=data[k]))
    db.commit()
    return schemas.ConfigOut(profile=_profile(db), integrations=_integration_status())
