"""
Announcements Agent — TIER 2 notice board.

Owner / staff / teachers post broadcasts targeted at a role group (and
optionally one class). Everyone reads the notices addressed to them via
/announcements/feed. Optional email blast reuses the notification sender.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
import notifications
from dependencies import get_db, require_school_member, get_current_user

router = APIRouter(prefix="/announcements", tags=["announcements"])

_ROLE_TO_AUDIENCE = {
    "student": "students", "parent": "parents",
    "teacher": "teachers", "staff": "staff",
}


def _require_announcer(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role not in ("owner", "staff", "teacher"):
        raise HTTPException(403, "Only owner, staff or teachers can post announcements.")
    return user


def _user_classes(db: Session, user: models.User) -> set[str] | None:
    """Classes that scope a user's feed. None = no class restriction (owner/staff)."""
    if user.role in ("owner", "staff"):
        return None
    if user.role == "teacher":
        t = db.query(models.Teacher).filter(models.Teacher.user_id == user.id).first()
        if not t or not t.classes_taught:
            return set()
        return {c.strip() for c in t.classes_taught.split(",") if c.strip()}
    if user.role == "student":
        s = db.query(models.Student).filter(models.Student.user_id == user.id).first()
        return {s.student_class} if s else set()
    if user.role == "parent":
        links = db.query(models.ParentLink).filter(
            models.ParentLink.parent_user_id == user.id,
            models.ParentLink.status == "approved",
        ).all()
        classes = set()
        for l in links:
            s = db.query(models.Student).filter(models.Student.id == l.student_id).first()
            if s:
                classes.add(s.student_class)
        return classes
    return set()


def feed_for(db: Session, user: models.User) -> list[models.Announcement]:
    """Announcements visible to this user, newest first."""
    rows = db.query(models.Announcement).order_by(
        models.Announcement.created_at.desc()).all()
    if user.role == "owner":
        return rows
    aud = _ROLE_TO_AUDIENCE.get(user.role)
    classes = _user_classes(db, user)
    out = []
    for a in rows:
        if a.audience not in ("all", aud):
            continue
        if a.student_class:
            if classes is not None and a.student_class not in classes:
                continue
        out.append(a)
    return out


def _email_audience(db: Session, ann: models.Announcement):
    """Best-effort email blast for a class-scoped announcement."""
    if not ann.student_class:
        return  # avoid school-wide blasts here; in-app feed covers those
    students = db.query(models.Student).filter(
        models.Student.student_class == ann.student_class,
        models.Student.status == "active",
    ).all()
    for s in students:
        notifications.notify_student(db, s, f"[Notice] {ann.title}", ann.body)


# ---------------- endpoints ---------------- #

@router.post("", response_model=schemas.AnnouncementOut)
def create(payload: schemas.AnnouncementCreate,
           db: Session = Depends(get_db),
           user: models.User = Depends(_require_announcer)):
    if payload.audience not in schemas.ANNOUNCEMENT_AUDIENCES:
        raise HTTPException(400, f"audience must be one of {schemas.ANNOUNCEMENT_AUDIENCES}")
    # Teachers may only target classes they teach.
    if user.role == "teacher" and payload.student_class:
        classes = _user_classes(db, user) or set()
        if payload.student_class not in classes:
            raise HTTPException(403, "You can only post to classes you teach.")
    ann = models.Announcement(
        title=payload.title, body=payload.body,
        audience=payload.audience, student_class=payload.student_class,
        created_by=user.id, created_by_name=user.name,
    )
    db.add(ann); db.commit(); db.refresh(ann)
    if payload.notify:
        _email_audience(db, ann)
    return ann


@router.get("/feed", response_model=list[schemas.AnnouncementOut])
def feed(db: Session = Depends(get_db),
         user: models.User = Depends(require_school_member)):
    return feed_for(db, user)


@router.get("", response_model=list[schemas.AnnouncementOut])
def list_all(db: Session = Depends(get_db),
             user: models.User = Depends(_require_announcer)):
    """Management list. Teachers see their own; owner/staff see everything."""
    q = db.query(models.Announcement)
    if user.role == "teacher":
        q = q.filter(models.Announcement.created_by == user.id)
    return q.order_by(models.Announcement.created_at.desc()).all()


@router.delete("/{announcement_id}")
def delete(announcement_id: int,
           db: Session = Depends(get_db),
           user: models.User = Depends(_require_announcer)):
    a = db.query(models.Announcement).filter(
        models.Announcement.id == announcement_id).first()
    if not a:
        raise HTTPException(404, "Announcement not found")
    if user.role == "teacher" and a.created_by != user.id:
        raise HTTPException(403, "You can only delete your own announcements.")
    db.delete(a); db.commit()
    return {"ok": True}
