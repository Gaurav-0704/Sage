"""
TIER 2 — announcement feed targeting tests.

feed_for is the core: audience-role + class scoping per viewer role.
"""

import pytest

import models
from agents import announcements_agent


def _ann(db, audience="all", student_class=None, title="t"):
    a = models.Announcement(title=title, body="b", audience=audience,
                            student_class=student_class)
    db.add(a); db.commit(); db.refresh(a)
    return a


@pytest.fixture()
def users(db):
    owner = models.User(name="O", email="o@t.com", password="x", role="owner", status="active")
    db.add(owner); db.commit(); db.refresh(owner)

    su = models.User(name="S", email="s@t.com", password="x", role="student", status="active")
    db.add(su); db.commit(); db.refresh(su)
    s = models.Student(admission_no="S1", name="S", student_class="5",
                       status="active", last_year_dues=0, user_id=su.id)
    db.add(s); db.commit()
    return {"owner": owner, "student": su}


class TestFeed:
    def test_all_audience_visible_to_student(self, db, users):
        _ann(db, audience="all")
        feed = announcements_agent.feed_for(db, users["student"])
        assert len(feed) == 1

    def test_teacher_audience_hidden_from_student(self, db, users):
        _ann(db, audience="teachers")
        feed = announcements_agent.feed_for(db, users["student"])
        assert feed == []

    def test_class_scoped_matches_student_class(self, db, users):
        _ann(db, audience="students", student_class="5")
        _ann(db, audience="students", student_class="6")
        feed = announcements_agent.feed_for(db, users["student"])
        assert len(feed) == 1
        assert feed[0].student_class == "5"

    def test_owner_sees_everything(self, db, users):
        _ann(db, audience="students", student_class="6")
        _ann(db, audience="teachers")
        feed = announcements_agent.feed_for(db, users["owner"])
        assert len(feed) == 2

    def test_parent_sees_childs_class(self, db, users):
        pu = models.User(name="P", email="p@t.com", password="x",
                         role="parent", status="active")
        db.add(pu); db.commit(); db.refresh(pu)
        s = db.query(models.Student).first()
        db.add(models.ParentLink(parent_user_id=pu.id, student_id=s.id, status="approved"))
        db.commit()
        _ann(db, audience="parents", student_class="5")
        _ann(db, audience="parents", student_class="9")
        feed = announcements_agent.feed_for(db, pu)
        assert len(feed) == 1
        assert feed[0].student_class == "5"
