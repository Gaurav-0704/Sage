"""
TIER 1a — Attendance tests.

Exercises the shared mark_attendance upsert + summarize logic directly against
the in-memory DB (same style as the other suites).
"""

from datetime import date, timedelta

import pytest

import models
from agents import attendance_agent


@pytest.fixture()
def class5(db):
    studs = []
    for i in range(3):
        s = models.Student(
            admission_no=f"C5{i:03d}", name=f"Kid {i}",
            student_class="5", section="A", status="active", last_year_dues=0,
        )
        db.add(s)
    db.commit()
    return db.query(models.Student).filter(models.Student.student_class == "5").all()


class TestMark:
    def test_creates_rows(self, db, class5):
        rows = [{"student_id": s.id, "status": "present"} for s in class5]
        res = attendance_agent.mark_attendance(
            db, student_class="5", section="A", on_date=date.today(),
            period=0, rows=rows, marked_by=None)
        db.commit()
        assert res["created"] == 3
        assert res["updated"] == 0
        assert db.query(models.Attendance).count() == 3

    def test_remark_updates_not_duplicates(self, db, class5):
        s = class5[0]
        attendance_agent.mark_attendance(
            db, student_class="5", section="A", on_date=date.today(),
            period=0, rows=[{"student_id": s.id, "status": "absent"}], marked_by=None)
        db.commit()
        res = attendance_agent.mark_attendance(
            db, student_class="5", section="A", on_date=date.today(),
            period=0, rows=[{"student_id": s.id, "status": "present"}], marked_by=None)
        db.commit()
        assert res["updated"] == 1
        assert db.query(models.Attendance).count() == 1
        assert db.query(models.Attendance).first().status == "present"

    def test_period_wise_is_separate_slot(self, db, class5):
        s = class5[0]
        for p in (0, 1, 2):
            attendance_agent.mark_attendance(
                db, student_class="5", section="A", on_date=date.today(),
                period=p, rows=[{"student_id": s.id, "status": "present"}], marked_by=None)
        db.commit()
        assert db.query(models.Attendance).filter(
            models.Attendance.student_id == s.id).count() == 3

    def test_invalid_status_collected(self, db, class5):
        s = class5[0]
        res = attendance_agent.mark_attendance(
            db, student_class="5", section="A", on_date=date.today(),
            period=0, rows=[{"student_id": s.id, "status": "vacation"}], marked_by=None)
        assert res["created"] == 0
        assert res["error_count"] == 1

    def test_student_outside_class_rejected(self, db, class5):
        other = models.Student(admission_no="C6001", name="Six", student_class="6",
                               status="active", last_year_dues=0)
        db.add(other); db.commit()
        res = attendance_agent.mark_attendance(
            db, student_class="5", section="A", on_date=date.today(),
            period=0, rows=[{"student_id": other.id, "status": "present"}], marked_by=None)
        assert res["created"] == 0
        assert res["error_count"] == 1


class TestSummarize:
    def test_percentage_counts_present_and_late(self, db, class5):
        s = class5[0]
        base = date.today()
        plan = {0: "present", 1: "late", 2: "absent", 3: "leave"}
        for i, status in plan.items():
            db.add(models.Attendance(student_id=s.id, date=base - timedelta(days=i),
                                     period=0, status=status))
        db.commit()
        tally = attendance_agent.summarize(db, [s.id])[s.id]
        assert tally["total"] == 4
        assert tally["present"] == 1
        assert tally["late"] == 1
        assert tally["absent"] == 1
        assert tally["leave"] == 1
        assert tally["percentage"] == 50.0   # (present+late)/total

    def test_empty_is_zero(self, db, class5):
        tally = attendance_agent.summarize(db, [class5[0].id])[class5[0].id]
        assert tally["total"] == 0
        assert tally["percentage"] == 0.0
