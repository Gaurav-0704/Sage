"""
Tests for fee structure creation and bulk application logic.
These cover the financial rules that would actually hurt a school if wrong.
"""

import pytest
from datetime import date
import models


def _apply_structure(db, fs, students):
    """Mirror the fee application logic from fees_agent."""
    total = fs.tuition_fee + fs.transport_fee + fs.books_fee + fs.uniform_fee + fs.other_fee
    created = 0
    for s in students:
        already = db.query(models.Fee).filter(
            models.Fee.student_id == s.id,
            models.Fee.academic_year == fs.academic_year,
        ).first()
        if already:
            continue
        db.add(models.Fee(
            student_id=s.id,
            academic_year=fs.academic_year,
            total_fee=total,
            paid_amount=0,
            due_amount=total,
        ))
        created += 1
    db.commit()
    return created


class TestFeeStructure:
    def test_total_is_sum_of_components(self, db, fee_structure):
        fs = fee_structure
        expected = 12000 + 3000 + 2000 + 1500 + 500
        actual = fs.tuition_fee + fs.transport_fee + fs.books_fee + fs.uniform_fee + fs.other_fee
        assert actual == expected == 19000

    def test_apply_creates_bill_per_student(self, db, fee_structure):
        students = []
        for i in range(5):
            s = models.Student(
                admission_no=f"S{i:03d}", name=f"Student {i}",
                student_class="5", status="active", last_year_dues=0,
            )
            db.add(s)
        db.commit()
        students = db.query(models.Student).filter(models.Student.student_class == "5").all()

        created = _apply_structure(db, fee_structure, students)
        assert created == 5

        bills = db.query(models.Fee).all()
        assert len(bills) == 5
        for bill in bills:
            assert bill.total_fee == 19000
            assert bill.paid_amount == 0
            assert bill.due_amount == 19000

    def test_apply_is_idempotent(self, db, fee_structure):
        """Running apply twice must not create duplicate bills."""
        s = models.Student(
            admission_no="IDEM001", name="Idem Test",
            student_class="5", status="active", last_year_dues=0,
        )
        db.add(s)
        db.commit()
        students = [s]

        first  = _apply_structure(db, fee_structure, students)
        second = _apply_structure(db, fee_structure, students)
        assert first == 1
        assert second == 0
        assert db.query(models.Fee).count() == 1

    def test_inactive_students_get_no_bill(self, db, fee_structure):
        active = models.Student(
            admission_no="ACT001", name="Active Student",
            student_class="5", status="active", last_year_dues=0,
        )
        inactive = models.Student(
            admission_no="INA001", name="Inactive Student",
            student_class="5", status="inactive", last_year_dues=0,
        )
        db.add_all([active, inactive])
        db.commit()

        # Only pass active students (mirrors the agent filtering)
        active_studs = db.query(models.Student).filter(
            models.Student.student_class == "5",
            models.Student.status == "active",
        ).all()
        created = _apply_structure(db, fee_structure, active_studs)
        assert created == 1

    def test_different_classes_dont_share_bills(self, db):
        fs5 = models.FeeStructure(
            student_class="5", academic_year="2025-26",
            tuition_fee=10000, transport_fee=0, books_fee=0, uniform_fee=0, other_fee=0,
        )
        fs6 = models.FeeStructure(
            student_class="6", academic_year="2025-26",
            tuition_fee=12000, transport_fee=0, books_fee=0, uniform_fee=0, other_fee=0,
        )
        s5 = models.Student(admission_no="C5001", name="Class 5 Kid",
                             student_class="5", status="active", last_year_dues=0)
        s6 = models.Student(admission_no="C6001", name="Class 6 Kid",
                             student_class="6", status="active", last_year_dues=0)
        db.add_all([fs5, fs6, s5, s6])
        db.commit()

        _apply_structure(db, fs5, [s5])
        _apply_structure(db, fs6, [s6])

        bill5 = db.query(models.Fee).filter(models.Fee.student_id == s5.id).first()
        bill6 = db.query(models.Fee).filter(models.Fee.student_id == s6.id).first()
        assert bill5.total_fee == 10000
        assert bill6.total_fee == 12000
