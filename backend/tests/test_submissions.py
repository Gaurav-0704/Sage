"""
TIER 2 — assignment submission + grading flow tests.

Exercises upsert_submission (create / re-submit / blocked-after-grade) and the
grade transition directly against the in-memory DB.
"""

from datetime import datetime

import pytest

import models
from agents import assignments_agent


@pytest.fixture()
def setup(db):
    u = models.User(name="T", email="t@test.com", password="x",
                    role="teacher", status="active")
    db.add(u); db.commit(); db.refresh(u)
    t = models.Teacher(user_id=u.id, employee_id="E1", classes_taught="5")
    db.add(t); db.commit(); db.refresh(t)
    a = models.Assignment(teacher_id=t.id, student_class="5", subject="Math",
                          title="HW1", max_marks=10)
    s = models.Student(admission_no="S1", name="Asha", student_class="5",
                       status="active", last_year_dues=0)
    db.add_all([a, s]); db.commit(); db.refresh(a); db.refresh(s)
    return a, s, u


class TestSubmit:
    def test_create_submission(self, db, setup):
        a, s, _ = setup
        sub = assignments_agent.upsert_submission(db, a, s, "my answer", None, None)
        db.commit()
        assert sub.status == "submitted"
        assert db.query(models.AssignmentSubmission).count() == 1

    def test_resubmit_updates_same_row(self, db, setup):
        a, s, _ = setup
        assignments_agent.upsert_submission(db, a, s, "first", None, None)
        db.commit()
        sub = assignments_agent.upsert_submission(db, a, s, "second", None, None)
        db.commit()
        assert db.query(models.AssignmentSubmission).count() == 1
        assert sub.text == "second"

    def test_cannot_resubmit_after_graded(self, db, setup):
        a, s, u = setup
        sub = assignments_agent.upsert_submission(db, a, s, "answer", None, None)
        db.commit()
        sub.status = "graded"; sub.marks_obtained = 8; db.commit()
        with pytest.raises(ValueError):
            assignments_agent.upsert_submission(db, a, s, "sneaky edit", None, None)


class TestEnrichment:
    def test_submission_out_has_assignment_context(self, db, setup):
        a, s, _ = setup
        sub = assignments_agent.upsert_submission(db, a, s, "x", None, None)
        db.commit()
        out = assignments_agent.submission_out(db, sub)
        assert out["student_name"] == "Asha"
        assert out["assignment_title"] == "HW1"
        assert out["max_marks"] == 10
