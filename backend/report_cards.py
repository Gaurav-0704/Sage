"""
Report-card PDF generation (TIER 2).

Pure-Python via fpdf2 (no system libs) so it runs anywhere the API runs.
`build_report_card` turns a student's marks for one exam into a graded PDF;
the data-shaping (`report_card_data`) is separated out so it's unit-testable
without rendering.
"""

from collections import defaultdict

from fpdf import FPDF
from sqlalchemy.orm import Session

import models

SCHOOL_NAME = "Sage"


def grade_for(pct: float) -> str:
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B"
    if pct >= 60: return "C"
    if pct >= 50: return "D"
    if pct >= 35: return "E"
    return "F"


def report_card_data(db: Session, student: models.Student, exam: models.Exam) -> dict:
    """Compute the report-card numbers + class rank for one student+exam."""
    marks = db.query(models.Mark).filter(
        models.Mark.exam_id == exam.id,
        models.Mark.student_id == student.id,
    ).order_by(models.Mark.subject).all()

    subjects = []
    total_obt = total_max = 0.0
    for m in marks:
        pct = (m.marks_obtained / m.max_marks * 100) if m.max_marks else 0
        subjects.append({
            "subject": m.subject,
            "obtained": m.marks_obtained,
            "max": m.max_marks,
            "grade": grade_for(pct),
        })
        total_obt += m.marks_obtained
        total_max += m.max_marks

    pct = (total_obt / total_max * 100) if total_max else 0

    # Class rank across all students who sat this exam.
    all_marks = db.query(models.Mark).filter(models.Mark.exam_id == exam.id).all()
    totals = defaultdict(lambda: {"obt": 0.0, "mx": 0.0})
    for m in all_marks:
        totals[m.student_id]["obt"] += m.marks_obtained
        totals[m.student_id]["mx"] += m.max_marks
    pcts = {sid: (t["obt"] / t["mx"] * 100) if t["mx"] else 0 for sid, t in totals.items()}
    ranked = sorted(pcts.items(), key=lambda kv: kv[1], reverse=True)
    rank = next((i + 1 for i, (sid, _) in enumerate(ranked) if sid == student.id), None)

    return {
        "subjects": subjects,
        "total_obtained": round(total_obt, 2),
        "total_max": round(total_max, 2),
        "percentage": round(pct, 2),
        "grade": grade_for(pct),
        "rank": rank,
        "class_size": len(pcts),
    }


def build_report_card(db: Session, student: models.Student, exam: models.Exam) -> bytes:
    """Render the report card PDF and return the raw bytes."""
    d = report_card_data(db, student, exam)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, SCHOOL_NAME, ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 7, "Report Card", ln=True, align="C")
    pdf.ln(4)

    # Student / exam info
    pdf.set_font("Helvetica", "", 11)
    info = [
        ("Student", student.name),
        ("Admission No", student.admission_no),
        ("Class", f"{student.student_class}{('-' + student.section) if student.section else ''}"),
        ("Exam", f"{exam.name} ({exam.academic_year})"),
    ]
    for label, value in info:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(40, 7, f"{label}:")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, str(value), ln=True)
    pdf.ln(3)

    # Marks table
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(230, 224, 212)
    pdf.cell(90, 9, "Subject", border=1, fill=True)
    pdf.cell(35, 9, "Obtained", border=1, align="C", fill=True)
    pdf.cell(35, 9, "Max", border=1, align="C", fill=True)
    pdf.cell(0, 9, "Grade", border=1, align="C", fill=True, ln=True)

    pdf.set_font("Helvetica", "", 11)
    for s in d["subjects"]:
        pdf.cell(90, 8, str(s["subject"]), border=1)
        pdf.cell(35, 8, f"{s['obtained']:g}", border=1, align="C")
        pdf.cell(35, 8, f"{s['max']:g}", border=1, align="C")
        pdf.cell(0, 8, s["grade"], border=1, align="C", ln=True)

    if not d["subjects"]:
        pdf.cell(0, 8, "No marks recorded for this exam.", border=1, ln=True, align="C")

    # Totals
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 9, "Total", border=1)
    pdf.cell(35, 9, f"{d['total_obtained']:g}", border=1, align="C")
    pdf.cell(35, 9, f"{d['total_max']:g}", border=1, align="C")
    pdf.cell(0, 9, d["grade"], border=1, align="C", ln=True)
    pdf.ln(4)

    # Summary line
    pdf.set_font("Helvetica", "", 11)
    rank_txt = f"{d['rank']} of {d['class_size']}" if d["rank"] else "—"
    pdf.cell(0, 7, f"Percentage: {d['percentage']}%    Overall grade: {d['grade']}    "
                   f"Class rank: {rank_txt}", ln=True)
    pdf.ln(14)

    # Signatures
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(90, 7, "____________________")
    pdf.cell(0, 7, "____________________", ln=True)
    pdf.cell(90, 6, "Class Teacher")
    pdf.cell(0, 6, "Principal", ln=True)

    out = pdf.output()
    return bytes(out)
