"""
TIER 1b — Timetable conflict-detection tests.

Exercises find_conflicts directly: slot-occupied and teacher-double-booked,
plus the exclude_id path used when editing an existing entry.
"""

import pytest

import models
from agents import timetable_agent


@pytest.fixture()
def teacher(db):
    u = models.User(name="T One", email="t1@sage.school", password="x",
                    role="teacher", status="active")
    db.add(u); db.commit(); db.refresh(u)
    t = models.Teacher(user_id=u.id, employee_id="E1", subject="Math",
                       classes_taught="5,6")
    db.add(t); db.commit(); db.refresh(t)
    return t


def _entry(db, cls="5", section="A", day="Mon", period=1, subject="Math", teacher_id=None):
    e = models.TimetableEntry(student_class=cls, section=section, day=day,
                              period=period, subject=subject, teacher_id=teacher_id)
    db.add(e); db.commit(); db.refresh(e)
    return e


class TestConflicts:
    def test_clean_slot_has_no_conflicts(self, db):
        c = timetable_agent.find_conflicts(
            db, student_class="5", section="A", day="Mon", period=1, teacher_id=None)
        assert c == []

    def test_slot_already_occupied(self, db):
        _entry(db, period=1, subject="Math")
        c = timetable_agent.find_conflicts(
            db, student_class="5", section="A", day="Mon", period=1, teacher_id=None)
        assert len(c) == 1
        assert "already has" in c[0]

    def test_teacher_double_booked_across_classes(self, db, teacher):
        _entry(db, cls="5", section="A", day="Mon", period=1, teacher_id=teacher.id)
        # same teacher, different class, same day+period
        c = timetable_agent.find_conflicts(
            db, student_class="6", section="A", day="Mon", period=1, teacher_id=teacher.id)
        assert any("already booked" in m for m in c)

    def test_teacher_free_at_other_period(self, db, teacher):
        _entry(db, cls="5", section="A", day="Mon", period=1, teacher_id=teacher.id)
        c = timetable_agent.find_conflicts(
            db, student_class="6", section="A", day="Mon", period=2, teacher_id=teacher.id)
        assert c == []

    def test_exclude_self_when_editing(self, db, teacher):
        e = _entry(db, cls="5", section="A", day="Mon", period=1, teacher_id=teacher.id)
        # editing the same row must not conflict with itself
        c = timetable_agent.find_conflicts(
            db, student_class="5", section="A", day="Mon", period=1,
            teacher_id=teacher.id, exclude_id=e.id)
        assert c == []
