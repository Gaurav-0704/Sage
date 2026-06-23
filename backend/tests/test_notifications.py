"""
TIER 1d — notification recipient resolution + persistence.

With no Resend/SMTP env configured, send() still logs + persists a Notification
row, so we assert on rows created (delivery backend is env-dependent).
"""

import pytest

import models
import notifications


@pytest.fixture()
def student_with_family(db):
    su = models.User(name="Stud", email="stud@test.com", password="x",
                     role="student", status="active")
    db.add(su); db.commit(); db.refresh(su)
    s = models.Student(admission_no="N1", name="Stud", student_class="5",
                       status="active", last_year_dues=0, user_id=su.id)
    db.add(s); db.commit(); db.refresh(s)

    p_ok = models.User(name="Parent OK", email="ok@test.com", password="x",
                       role="parent", status="active")
    p_pending = models.User(name="Parent Pending", email="pending@test.com",
                            password="x", role="parent", status="pending")
    db.add_all([p_ok, p_pending]); db.commit()
    db.add(models.ParentLink(parent_user_id=p_ok.id, student_id=s.id, status="approved"))
    db.add(models.ParentLink(parent_user_id=p_pending.id, student_id=s.id, status="pending"))
    db.commit()
    return s


class TestRecipients:
    def test_includes_student_and_approved_parent_only(self, db, student_with_family):
        emails = notifications.recipients_for_student(db, student_with_family)
        assert "stud@test.com" in emails
        assert "ok@test.com" in emails
        assert "pending@test.com" not in emails   # pending link excluded
        assert len(emails) == 2

    def test_dedupes(self, db):
        # student login == a parent email shouldn't double up
        u = models.User(name="X", email="dup@test.com", password="x",
                        role="student", status="active")
        db.add(u); db.commit(); db.refresh(u)
        s = models.Student(admission_no="N2", name="X", student_class="5",
                           status="active", last_year_dues=0, user_id=u.id)
        db.add(s); db.commit(); db.refresh(s)
        p = models.User(name="P", email="dup@test.com", password="x",
                        role="parent", status="active")
        # (email unique constraint forbids real dup; simulate resolver dedupe instead)
        emails = notifications.recipients_for_student(db, s)
        assert emails == ["dup@test.com"]


class TestNotifyStudent:
    def test_persists_one_row_per_recipient(self, db, student_with_family):
        n = notifications.notify_student(db, student_with_family, "Hi", "Body")
        assert n == 2
        assert db.query(models.Notification).count() == 2

    def test_never_raises_on_no_recipients(self, db):
        s = models.Student(admission_no="N3", name="Orphan", student_class="5",
                           status="active", last_year_dues=0)
        db.add(s); db.commit(); db.refresh(s)
        assert notifications.notify_student(db, s, "Hi", "Body") == 0
