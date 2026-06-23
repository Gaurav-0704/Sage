"""
TIER 1c — Parent claim/verify + link approval tests.

Exercises verify_and_link (the shared verification rule) and the approved-child
access guard directly against the in-memory DB.
"""

import pytest

import models
from agents import parents_agent


@pytest.fixture()
def parent_user(db):
    u = models.User(name="Parent P", email="parent@test.com", password="x",
                    role="parent", status="pending")
    db.add(u); db.commit(); db.refresh(u)
    return u


@pytest.fixture()
def kid(db):
    s = models.Student(admission_no="ADM100", name="Kid K", student_class="5",
                       section="A", phone="98765 43210", status="active", last_year_dues=0)
    db.add(s); db.commit(); db.refresh(s)
    return s


class TestClaim:
    def test_phone_match_creates_pending_link(self, db, parent_user, kid):
        link = parents_agent.verify_and_link(db, parent_user.id, "ADM100", "9876543210")
        db.commit()
        assert link.status == "pending"
        assert link.student_id == kid.id

    def test_phone_mismatch_rejected(self, db, parent_user, kid):
        with pytest.raises(ValueError):
            parents_agent.verify_and_link(db, parent_user.id, "ADM100", "1111111111")

    def test_unknown_admission_rejected(self, db, parent_user):
        with pytest.raises(ValueError):
            parents_agent.verify_and_link(db, parent_user.id, "NOPE", "9876543210")

    def test_duplicate_claim_rejected(self, db, parent_user, kid):
        parents_agent.verify_and_link(db, parent_user.id, "ADM100", "9876543210")
        db.commit()
        with pytest.raises(ValueError):
            parents_agent.verify_and_link(db, parent_user.id, "ADM100", "9876543210")


class TestAccessGuard:
    def test_approved_ids(self, db, parent_user, kid):
        link = parents_agent.verify_and_link(db, parent_user.id, "ADM100", "9876543210")
        db.commit()
        assert parents_agent._approved_student_ids(db, parent_user.id) == []
        link.status = "approved"; db.commit()
        assert parents_agent._approved_student_ids(db, parent_user.id) == [kid.id]

    def test_require_child_blocks_unapproved(self, db, parent_user, kid):
        parents_agent.verify_and_link(db, parent_user.id, "ADM100", "9876543210")
        db.commit()
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            parents_agent._require_child(db, parent_user.id, kid.id)
