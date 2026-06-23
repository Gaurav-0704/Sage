"""
TIER 2 — report-card data + PDF generation.

report_card_data is the testable core (totals, percentage, grade, rank);
build_report_card is smoke-tested to confirm it produces real PDF bytes.
"""

import pytest

import models
import report_cards


@pytest.fixture()
def exam_with_marks(db):
    exam = models.Exam(name="Term 1", academic_year="2025-26", student_class="5")
    db.add(exam); db.commit(); db.refresh(exam)

    # topper + our student so rank is meaningful
    topper = models.Student(admission_no="T1", name="Topper", student_class="5",
                            status="active", last_year_dues=0)
    s = models.Student(admission_no="S1", name="Asha", student_class="5",
                       section="A", status="active", last_year_dues=0)
    db.add_all([topper, s]); db.commit(); db.refresh(topper); db.refresh(s)

    db.add_all([
        models.Mark(exam_id=exam.id, student_id=s.id, subject="Math",
                    max_marks=100, marks_obtained=80),
        models.Mark(exam_id=exam.id, student_id=s.id, subject="English",
                    max_marks=100, marks_obtained=70),
        models.Mark(exam_id=exam.id, student_id=topper.id, subject="Math",
                    max_marks=100, marks_obtained=99),
        models.Mark(exam_id=exam.id, student_id=topper.id, subject="English",
                    max_marks=100, marks_obtained=99),
    ])
    db.commit()
    return exam, s, topper


class TestData:
    def test_totals_and_grade(self, db, exam_with_marks):
        exam, s, _ = exam_with_marks
        d = report_cards.report_card_data(db, s, exam)
        assert d["total_obtained"] == 150
        assert d["total_max"] == 200
        assert d["percentage"] == 75.0
        assert d["grade"] == "B"
        assert len(d["subjects"]) == 2

    def test_rank_against_class(self, db, exam_with_marks):
        exam, s, _ = exam_with_marks
        d = report_cards.report_card_data(db, s, exam)
        assert d["rank"] == 2          # topper is #1
        assert d["class_size"] == 2

    def test_no_marks_is_zero(self, db):
        exam = models.Exam(name="Empty", academic_year="2025-26", student_class="5")
        s = models.Student(admission_no="Z1", name="Z", student_class="5",
                           status="active", last_year_dues=0)
        db.add_all([exam, s]); db.commit(); db.refresh(exam); db.refresh(s)
        d = report_cards.report_card_data(db, s, exam)
        assert d["total_max"] == 0
        assert d["percentage"] == 0
        assert d["grade"] == "F"


class TestPDF:
    def test_build_returns_pdf_bytes(self, db, exam_with_marks):
        exam, s, _ = exam_with_marks
        pdf = report_cards.build_report_card(db, s, exam)
        assert isinstance(pdf, (bytes, bytearray))
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 500


def test_grade_boundaries():
    assert report_cards.grade_for(95) == "A+"
    assert report_cards.grade_for(85) == "A"
    assert report_cards.grade_for(34) == "F"
