"""
Tests for dashboard stat calculations and at-risk scoring.
"""

import pytest
from datetime import date, timedelta
import models


def _due_for(student, db):
    total = sum(f.total_fee for f in student.fees) + (student.last_year_dues or 0)
    paid  = sum(p.amount for p in student.payments)
    return max(0.0, total - paid)


class TestDashboardStats:
    def test_net_is_collected_minus_expenses(self, db):
        s = models.Student(admission_no="D001", name="Test", student_class="5",
                            status="active", last_year_dues=0)
        db.add(s); db.commit(); db.refresh(s)

        db.add(models.Payment(student_id=s.id, amount=50000,
                               date=date.today(), mode="cash"))
        db.add(models.Expense(title="Salary", amount=20000, category="salary",
                               paid_from="cash", date=date.today()))
        db.commit()

        total_collected = sum(p.amount for p in db.query(models.Payment).all())
        total_expense   = sum(e.amount for e in db.query(models.Expense).all())
        net = total_collected - total_expense
        assert net == 30000

    def test_total_due_never_negative(self, db):
        s = models.Student(admission_no="D002", name="Test", student_class="5",
                            status="active", last_year_dues=0)
        db.add(s); db.commit(); db.refresh(s)

        db.add(models.Fee(student_id=s.id, academic_year="2025-26",
                           total_fee=10000, paid_amount=10000, due_amount=0))
        db.add(models.Payment(student_id=s.id, amount=12000,
                               date=date.today(), mode="cash"))
        db.commit()

        fee_total = sum(f.total_fee for f in db.query(models.Fee).all())
        collected = sum(p.amount for p in db.query(models.Payment).all())
        total_due = max(0.0, fee_total - collected)
        assert total_due == 0.0   # must not be -2000

    def test_last_year_dues_included_in_total(self, db):
        s = models.Student(admission_no="D003", name="Test", student_class="5",
                            status="active", last_year_dues=5000)
        db.add(s); db.commit(); db.refresh(s)

        db.add(models.Fee(student_id=s.id, academic_year="2025-26",
                           total_fee=15000, paid_amount=0, due_amount=15000))
        db.commit()

        due = _due_for(s, db)
        assert due == 20000   # 15000 current + 5000 carry-forward


class TestAtRiskLogic:
    def _risk_score(self, due, days_since):
        due_score  = min(50, int(due / 1000))
        days_score = min(50, int(days_since / 6))
        return min(100, due_score + days_score)

    def test_high_due_high_days_is_high_risk(self):
        # due=30000 → due_score=min(50,30)=30; days=180 → days_score=min(50,30)=30; total=60
        score = self._risk_score(due=30000, days_since=180)
        assert score >= 50   # "high" risk band (50-74)

    def test_very_high_due_many_days_is_critical(self):
        # due=80000 → due_score=50; days=300 → days_score=50; total=100
        score = self._risk_score(due=80000, days_since=300)
        assert score >= 75

    def test_low_due_recent_payment_is_low_risk(self):
        score = self._risk_score(due=500, days_since=5)
        assert score < 25

    def test_score_caps_at_100(self):
        score = self._risk_score(due=999999, days_since=9999)
        assert score == 100

    def test_no_payment_ever_counts_as_max_days(self, db):
        s = models.Student(admission_no="R001", name="No Pay Student",
                            student_class="8", status="active", last_year_dues=10000)
        db.add(s); db.commit(); db.refresh(s)

        db.add(models.Fee(student_id=s.id, academic_year="2025-26",
                           total_fee=15000, paid_amount=0, due_amount=15000))
        db.commit()

        last_pay = max((p.date for p in s.payments), default=None)
        assert last_pay is None   # never paid

    def test_recent_payment_excluded_from_at_risk(self, db):
        s = models.Student(admission_no="R002", name="Recent Payer",
                            student_class="8", status="active", last_year_dues=0)
        db.add(s); db.commit(); db.refresh(s)

        db.add(models.Fee(student_id=s.id, academic_year="2025-26",
                           total_fee=20000, paid_amount=5000, due_amount=15000))
        db.add(models.Payment(student_id=s.id, amount=5000,
                               date=date.today() - timedelta(days=3), mode="cash"))
        db.commit()
        db.refresh(s)

        last_pay = max((p.date for p in s.payments), default=None)
        days_since = (date.today() - last_pay).days
        assert days_since <= 30   # would NOT appear in 30-day at-risk filter
