"""
Records (registrar) agent — owner only.

Two responsibilities:

  1. Maintains data/students_master.csv as the registrar's archive.
     Includes every student that has ever existed in the database, with
     computed financial totals appended. The actual write is done by
     csv_sync.sync_records() and is triggered automatically whenever
     students_agent CRUDs anything.

  2. Generates printable Bonafide Certificates, Transfer Certificates
     and exam Memos. Each comes back as an HTML page that auto-opens
     the browser print dialog — pick a real printer or "Save as PDF"
     in the destination dropdown.

The agent does NOT modify student data — students_agent owns that. It
just reads from the database and prints.
"""

import io
from datetime import datetime, date as Date
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

import models
from csv_sync import sync_records, RECORDS_CSV
from dependencies import get_db, require_owner
from school_constants import (
    SCHOOL_NAME, SCHOOL_ADDRESS, SCHOOL_PHONE, class_sort_key,
)

router = APIRouter(prefix="/records", tags=["records"])


# ───────────────────── helpers ───────────────────── #

def _grade(pct: float) -> str:
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B"
    if pct >= 60: return "C"
    if pct >= 50: return "D"
    if pct >= 35: return "E"
    return "F"


def _fmt_date(d) -> str:
    if not d:
        return "_______________"
    if hasattr(d, "strftime"):
        return d.strftime("%d %B %Y")
    return str(d)


def _pronoun(gender: Optional[str]) -> tuple[str, str, str]:
    """Returns (he/she, his/her, son/daughter) based on gender."""
    g = (gender or "").upper()
    if g == "F":
        return ("she", "her", "daughter")
    if g == "M":
        return ("he", "his", "son")
    return ("they", "their", "child")


# ───────────────────── student lookup ───────────────────── #

@router.get("/students")
def search_students(
    q: str | None = Query(None),
    include_inactive: bool = Query(True),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    """Search the master archive (active + inactive + alumni).

    Returns enough fields to populate the picker without exposing
    Aadhaar (which is hidden from the response since the picker
    doesn't need it).
    """
    query = db.query(models.Student)
    if not include_inactive:
        query = query.filter(models.Student.status == "active")
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            models.Student.name.ilike(like),
            models.Student.admission_no.ilike(like),
            models.Student.parent_name.ilike(like),
        ))
    rows = query.all()
    rows.sort(key=lambda s: (class_sort_key(s.student_class),
                              s.section or "", s.name or ""))
    return [{
        "id":           s.id,
        "name":         s.name,
        "admission_no": s.admission_no,
        "student_class": s.student_class,
        "section":      s.section,
        "parent_name":  s.parent_name,
        "status":       s.status,
    } for s in rows[:200]]


@router.get("/students/{student_id}/exams")
def student_exams(
    student_id: int,
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    """List exams that this student has marks for (for the Memo flow)."""
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s:
        raise HTTPException(404, "Student not found")
    exam_ids = {m.exam_id for m in db.query(models.Mark)
                                      .filter(models.Mark.student_id == student_id).all()}
    if not exam_ids:
        return []
    exams = db.query(models.Exam).filter(models.Exam.id.in_(exam_ids)) \
              .order_by(models.Exam.date.desc(), models.Exam.id.desc()).all()
    return [{
        "id": e.id, "name": e.name,
        "academic_year": e.academic_year,
        "student_class": e.student_class,
        "date": e.date.isoformat() if e.date else None,
    } for e in exams]


# ───────────────────── master CSV ───────────────────── #

@router.get("/master.csv")
def download_master(db: Session = Depends(get_db),
                    _owner: models.User = Depends(require_owner)):
    """Force a fresh write of the master archive then stream it."""
    sync_records(db)
    if not RECORDS_CSV.exists():
        raise HTTPException(500, "Master file could not be generated.")
    today = Date.today().isoformat()
    return StreamingResponse(
        iter([RECORDS_CSV.read_text(encoding="utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition":
                  f'attachment; filename="students_master_{today}.csv"'},
    )


@router.post("/sync")
def manual_sync(db: Session = Depends(get_db),
                _owner: models.User = Depends(require_owner)):
    """Owner-triggered re-sync of the master archive."""
    ok = sync_records(db)
    return {"ok": ok, "path": str(RECORDS_CSV)}


# ───────────────────── document templates ───────────────────── #

_SHARED_STYLE = """
  @page  { size: A4; margin: 18mm; }
  body   { font-family: "Times New Roman", Georgia, serif; color: #111;
           max-width: 720px; margin: 30px auto; padding: 30px;
           border: 2px solid #111; line-height: 1.55; }
  .head  { text-align: center; padding-bottom: 14px;
           border-bottom: 3px double #111; margin-bottom: 22px; }
  .head h1 { margin: 0; font-size: 28px; letter-spacing: .04em;
             text-transform: uppercase; }
  .head .addr { font-size: 12px; color: #444; margin-top: 4px; }
  .doc-title { text-align: center; margin: 26px 0 22px;
               font-size: 18px; font-weight: 700;
               letter-spacing: .12em; text-transform: uppercase;
               text-decoration: underline; }
  .meta { display: flex; justify-content: space-between; font-size: 13px;
          margin-bottom: 22px; }
  .body p { margin: 10px 0; font-size: 14px; text-align: justify; }
  .body strong { font-weight: 700; }
  table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 13px; }
  table th, table td { border: 1px solid #444; padding: 7px 10px; text-align: left; }
  table th { background: #f0f0f0; font-weight: 700; }
  table .num { text-align: right; font-variant-numeric: tabular-nums; }
  .signbox { display: flex; justify-content: space-between;
              margin-top: 60px; font-size: 13px; }
  .signbox .col { width: 40%; text-align: center;
                  padding-top: 8px; border-top: 1px solid #222; }
  .seal { float: right; width: 110px; height: 110px; border: 1.5px dashed #888;
          border-radius: 50%; display: grid; place-items: center;
          color: #888; font-size: 11px; margin: 18px 0 0 18px;
          font-style: italic; }
  .actions { text-align: center; margin: 22px 0 6px; }
  .actions button { padding: 9px 20px; border: 1px solid #2f6bff; background: #2f6bff;
                    color: #fff; border-radius: 6px; font-size: 13px; cursor: pointer;
                    margin: 0 4px; font-weight: 600; }
  .actions button.sec { background: #fff; color: #2f6bff; }
  @media print { .actions { display: none; } body { border: none; margin: 0; } }
"""

_AUTO_PRINT = """
<script>
  window.addEventListener('load', () => setTimeout(() => window.print(), 250));
</script>
"""


def _letterhead() -> str:
    return f"""
<div class="head">
  <h1>{SCHOOL_NAME}</h1>
  <div class="addr">{SCHOOL_ADDRESS} &middot; Phone: {SCHOOL_PHONE}</div>
</div>
"""


def _footer_signature(role: str = "Principal") -> str:
    return f"""
<div class="seal">School Seal</div>
<div class="signbox">
  <div class="col">Class Teacher</div>
  <div class="col">{role}</div>
</div>

<div class="actions">
  <button onclick="window.print()">🖨 Print / Save as PDF</button>
  <button class="sec" onclick="window.close()">Close</button>
</div>
"""


# ───────────────────── Bonafide ───────────────────── #

@router.get("/bonafide/{student_id}", response_class=HTMLResponse)
def bonafide(
    student_id: int,
    purpose: str = Query("whatever purpose it may be required",
                          description="Purpose of issuance"),
    ref_no: Optional[str] = Query(None,
                                    description="Custom reference number"),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s:
        raise HTTPException(404, "Student not found")

    she_he, her_his, son_daughter = _pronoun(s.gender)
    issued_on = datetime.now().strftime("%d %B %Y")
    ref = ref_no or f"SGE/BC/{s.id:04d}/{datetime.now():%y%m%d}"

    body = f"""
<p>This is to certify that <strong>{s.name}</strong>, {son_daughter} of
<strong>{s.parent_name or "________________"}</strong>, bearing admission number
<strong>{s.admission_no}</strong>, is a bonafide student of this school.</p>

<p>{she_he.capitalize()} is currently studying in
<strong>Class {s.student_class}{('-' + s.section) if s.section else ''}</strong>.
According to our records, {her_his} date of birth is
<strong>{_fmt_date(s.dob)}</strong>, and {she_he} was admitted to this institution
on <strong>{_fmt_date(s.admission_date)}</strong>.</p>

<p>{her_his.capitalize()} conduct and progress at school are satisfactory.</p>

<p>This certificate is issued for <strong>{purpose}</strong> at the request of
the parent / guardian.</p>
"""

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>Bonafide Certificate — {s.name}</title>
<style>{_SHARED_STYLE}</style>
</head><body>
{_letterhead()}
<div class="meta">
  <div>Ref. No: <strong>{ref}</strong></div>
  <div>Date: <strong>{issued_on}</strong></div>
</div>
<div class="doc-title">Bonafide Certificate</div>
<div class="body">{body}</div>
{_footer_signature()}
{_AUTO_PRINT}
</body></html>"""
    return HTMLResponse(html)


# ───────────────────── Transfer Certificate ───────────────────── #

@router.get("/tc/{student_id}", response_class=HTMLResponse)
def transfer_certificate(
    student_id: int,
    reason: str = Query("Parent's request",
                          description="Reason for leaving"),
    leaving_date: Optional[str] = Query(None,
                                          description="YYYY-MM-DD"),
    last_exam_passed: Optional[str] = Query(None,
                                              description="e.g. 'Class 9 Annual 2024-25'"),
    conduct: str = Query("Good"),
    dues_paid: bool = Query(True),
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s:
        raise HTTPException(404, "Student not found")

    leave_d = "_______________"
    if leaving_date:
        try:
            leave_d = _fmt_date(Date.fromisoformat(leaving_date))
        except ValueError:
            leave_d = leaving_date
    elif s.status in ("inactive", "alumni"):
        leave_d = _fmt_date(Date.today())

    issued_on = datetime.now().strftime("%d %B %Y")
    tc_no = f"SGE/TC/{s.id:04d}/{datetime.now():%y%m}"

    rows = [
        ("Name of student",         s.name),
        ("Father / Guardian",       s.parent_name or "—"),
        ("Date of birth",           _fmt_date(s.dob)),
        ("Aadhaar number",          s.aadhaar or "—"),
        ("Admission number",        s.admission_no),
        ("Date of admission",       _fmt_date(s.admission_date)),
        ("Class last attended",     f"{s.student_class}{('-' + s.section) if s.section else ''}"),
        ("Date of leaving",         leave_d),
        ("Reason for leaving",      reason),
        ("Conduct",                 conduct),
        ("All dues paid",           "Yes" if dues_paid else "No"),
        ("Last exam passed",        last_exam_passed or "As per records"),
    ]
    table_rows = "".join(
        f"<tr><th style='width:42%'>{i+1}. {label}</th><td>{value}</td></tr>"
        for i, (label, value) in enumerate(rows)
    )

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>Transfer Certificate — {s.name}</title>
<style>{_SHARED_STYLE}</style>
</head><body>
{_letterhead()}
<div class="meta">
  <div>TC No: <strong>{tc_no}</strong></div>
  <div>Issued on: <strong>{issued_on}</strong></div>
</div>
<div class="doc-title">Transfer Certificate</div>
<table>
  {table_rows}
</table>
<div class="body" style="font-size:12.5px; color:#444; margin-top:14px;">
  <p>Certified that the particulars given above are correct as per the
  records maintained by this school.</p>
</div>
{_footer_signature()}
{_AUTO_PRINT}
</body></html>"""
    return HTMLResponse(html)


# ───────────────────── Memo / Mark Sheet ───────────────────── #

@router.get("/memo/{student_id}/{exam_id}", response_class=HTMLResponse)
def memo(
    student_id: int,
    exam_id: int,
    db: Session = Depends(get_db),
    _owner: models.User = Depends(require_owner),
):
    s = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not s:
        raise HTTPException(404, "Student not found")
    e = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not e:
        raise HTTPException(404, "Exam not found")
    marks = db.query(models.Mark).filter(
        models.Mark.student_id == student_id,
        models.Mark.exam_id == exam_id,
    ).all()
    if not marks:
        raise HTTPException(404, "No marks recorded for this student in this exam")

    rows = []
    total_obt = 0.0
    total_max = 0.0
    for m in sorted(marks, key=lambda x: x.subject):
        pct = (m.marks_obtained / m.max_marks * 100) if m.max_marks else 0
        rows.append(
            f"<tr>"
            f"<td>{m.subject}</td>"
            f"<td class='num'>{m.max_marks:g}</td>"
            f"<td class='num'>{m.marks_obtained:g}</td>"
            f"<td class='num'>{pct:.1f}%</td>"
            f"<td>{_grade(pct)}</td>"
            f"</tr>"
        )
        total_obt += m.marks_obtained
        total_max += m.max_marks

    overall_pct = (total_obt / total_max * 100) if total_max else 0
    overall_grade = _grade(overall_pct)
    result = "PASS" if overall_pct >= 35 else "FAIL"
    issued_on = datetime.now().strftime("%d %B %Y")

    # In words for the total
    def _amount_in_words(n: float) -> str:
        return f"{n:g} out of {total_max:g}"

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<title>Memo — {s.name} — {e.name}</title>
<style>{_SHARED_STYLE}
  .summary {{ display: flex; justify-content: space-between;
              margin-top: 14px; font-size: 14px; }}
  .summary div {{ background: #f3f3f3; padding: 8px 14px; border-radius: 6px; }}
  .pass {{ color: #16a34a; font-weight: 700; }}
  .fail {{ color: #b91c1c; font-weight: 700; }}
</style>
</head><body>
{_letterhead()}
<div class="meta">
  <div>Roll / Adm No: <strong>{s.admission_no}</strong></div>
  <div>Date: <strong>{issued_on}</strong></div>
</div>
<div class="doc-title">Statement of Marks</div>

<table>
  <tr><th style="width:30%">Name of student</th><td>{s.name}</td></tr>
  <tr><th>Father / Guardian</th><td>{s.parent_name or '—'}</td></tr>
  <tr><th>Class &amp; Section</th><td>{s.student_class}{('-' + s.section) if s.section else ''}</td></tr>
  <tr><th>Examination</th><td>{e.name} &middot; {e.academic_year}</td></tr>
  <tr><th>Examination held on</th><td>{_fmt_date(e.date)}</td></tr>
</table>

<table>
  <tr>
    <th style="width:34%">Subject</th>
    <th class="num" style="width:14%">Max marks</th>
    <th class="num" style="width:14%">Obtained</th>
    <th class="num" style="width:14%">%</th>
    <th style="width:14%">Grade</th>
  </tr>
  {''.join(rows)}
  <tr style="background:#f0f0f0; font-weight:700;">
    <td>Total</td>
    <td class="num">{total_max:g}</td>
    <td class="num">{total_obt:g}</td>
    <td class="num">{overall_pct:.1f}%</td>
    <td>{overall_grade}</td>
  </tr>
</table>

<div class="summary">
  <div>Total marks: <strong>{_amount_in_words(total_obt)}</strong></div>
  <div>Percentage: <strong>{overall_pct:.2f}%</strong></div>
  <div>Grade: <strong>{overall_grade}</strong></div>
  <div>Result: <span class="{'pass' if result == 'PASS' else 'fail'}">{result}</span></div>
</div>

{_footer_signature()}
{_AUTO_PRINT}
</body></html>"""
    return HTMLResponse(html)
