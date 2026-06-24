"""
Demo data seeder — makes a fresh deploy immediately explorable.

Idempotent: does nothing if any student already exists. Enabled when the
SEED_DEMO env var is truthy (the single-service Docker image sets it). Everything
here is fake and editable from the UI — replace it with real data any time.

Demo logins (all changeable in Settings / via the owner):
    owner    owner@sage.school    / owner123     (seeded in main.seed_defaults)
    staff    staff@sage.school    / staff123
    teacher  teacher1@sage.school / teacher123
    student  student1@sage.school / student123
    parent   parent1@sage.school  / parent123    (linked to Aarav, class 5)
"""

from datetime import date, timedelta

import auth
import models


def _user(db, name, email, role, pw, **extra):
    u = db.query(models.User).filter(models.User.email == email).first()
    if u:
        return u
    extra.setdefault("status", "active")
    u = models.User(name=name, email=email, password=auth.hash_password(pw),
                    role=role, **extra)
    db.add(u); db.flush()
    return u


def seed_demo(db) -> bool:
    """Populate demo data. Returns True if it seeded, False if already present."""
    if db.query(models.Student).count() > 0:
        return False

    yr = "2025-26"

    # ---- teachers (User + Teacher) ----
    t1u = _user(db, "Meena Sharma", "teacher1@sage.school", "teacher", "teacher123",
                can_do_front_office=True)
    t2u = _user(db, "Rahul Verma", "teacher2@sage.school", "teacher", "teacher123")
    t1 = models.Teacher(user_id=t1u.id, employee_id="SGET001", subject="Math",
                        classes_taught="5,6", qualification="M.Sc, B.Ed", phone="9000000001")
    t2 = models.Teacher(user_id=t2u.id, employee_id="SGET002", subject="Science",
                        classes_taught="5,6", qualification="M.Sc", phone="9000000002")
    db.add_all([t1, t2]); db.flush()

    # ---- students ----
    names5 = ["Aarav Gupta", "Diya Singh", "Vihaan Rao", "Anaya Iyer",
              "Kabir Khan", "Myra Nair"]
    names6 = ["Reyansh Das", "Saanvi Menon", "Arjun Pillai", "Ira Bose"]
    students = []
    n = 1
    for cls, names in (("5", names5), ("6", names6)):
        for nm in names:
            s = models.Student(
                admission_no=f"SGE{n:04d}", name=nm, student_class=cls, section="A",
                gender="M" if n % 2 else "F", parent_name=nm.split()[-1] + " (parent)",
                phone=f"98765{n:05d}", status="active", last_year_dues=0,
                dob=date(2014, (n % 12) + 1, (n % 27) + 1),
                admission_date=date(2024, 6, 1),
            )
            db.add(s); students.append(s); n += 1
    db.flush()

    # ---- a student login for the first student ----
    s1 = students[0]
    s1u = _user(db, s1.name, "student1@sage.school", "student", "student123")
    s1.user_id = s1u.id

    # ---- a parent, approved-linked to the first student ----
    pu = _user(db, "Parent of " + s1.name.split()[0], "parent1@sage.school", "parent",
               "parent123", status="active")
    db.add(models.ParentLink(parent_user_id=pu.id, student_id=s1.id, status="approved"))

    # ---- fee structures + apply + a couple of payments ----
    for cls, tuition in (("5", 12000), ("6", 14000)):
        fs = models.FeeStructure(student_class=cls, academic_year=yr,
                                 tuition_fee=tuition, transport_fee=3000, books_fee=2000,
                                 uniform_fee=1500, other_fee=500)
        db.add(fs)
    db.flush()
    for s in students:
        total = 19000 if s.student_class == "5" else 21000
        db.add(models.Fee(student_id=s.id, academic_year=yr, total_fee=total,
                          paid_amount=0, due_amount=total))
    db.flush()
    # Two students pay something (settles oldest fee first).
    for s, amt in ((students[0], 10000), (students[1], 19000)):
        fee = db.query(models.Fee).filter(models.Fee.student_id == s.id).first()
        applied = min(amt, fee.due_amount)
        fee.paid_amount += applied; fee.due_amount -= applied
        db.add(models.Payment(student_id=s.id, amount=amt, date=date.today(),
                              mode="cash", fee_head="Tuition", note="Demo payment"))

    # ---- exam + marks for class 5 ----
    exam = models.Exam(name="Term 1", academic_year=yr, student_class="5",
                       date=date.today() - timedelta(days=10))
    db.add(exam); db.flush()
    subjects = [("Math", 100), ("English", 100), ("Science", 100)]
    for i, s in enumerate([s for s in students if s.student_class == "5"]):
        for subj, mx in subjects:
            db.add(models.Mark(exam_id=exam.id, student_id=s.id, subject=subj,
                               max_marks=mx, marks_obtained=60 + (i * 5 + hash(subj)) % 38))

    # ---- attendance: last 3 weekdays for class 5 ----
    cls5 = [s for s in students if s.student_class == "5"]
    d = date.today()
    days = 0
    while days < 3:
        if d.weekday() < 5:
            for j, s in enumerate(cls5):
                status = "absent" if (j + days) % 7 == 0 else "present"
                db.add(models.Attendance(student_id=s.id, date=d, period=0,
                                         status=status, marked_by=t1u.id))
            days += 1
        d -= timedelta(days=1)

    # ---- timetable for class 5A ----
    plan = [("Mon", 1, "Math", t1.id, "101"), ("Mon", 2, "Science", t2.id, "101"),
            ("Tue", 1, "Science", t2.id, "101"), ("Tue", 2, "Math", t1.id, "101"),
            ("Wed", 1, "Math", t1.id, "101"), ("Thu", 1, "Science", t2.id, "101"),
            ("Fri", 1, "Math", t1.id, "101")]
    for day, period, subj, tid, room in plan:
        db.add(models.TimetableEntry(student_class="5", section="A", day=day,
                                     period=period, subject=subj, teacher_id=tid,
                                     room=room, academic_year=yr))

    # ---- assignment + a graded submission ----
    a = models.Assignment(teacher_id=t1.id, student_class="5", section="A",
                          subject="Math", title="Fractions worksheet",
                          description="Complete exercises 1-10.",
                          due_date=date.today() + timedelta(days=5), max_marks=10)
    db.add(a); db.flush()
    db.add(models.AssignmentSubmission(
        assignment_id=a.id, student_id=s1.id, text="Done, attached my work.",
        status="graded", marks_obtained=8, feedback="Good work — check Q7.",
        graded_by=t1u.id))

    # ---- announcements ----
    db.add(models.Announcement(title="Welcome to Sage", body="This is a demo school. "
                               "Explore as owner, teacher, student or parent.",
                               audience="all", created_by=None, created_by_name="School"))
    db.add(models.Announcement(title="PTM this Friday", body="Parent-teacher meeting for "
                               "Class 5 on Friday at 10 AM.", audience="parents",
                               student_class="5", created_by=None, created_by_name="School"))

    db.commit()
    return True
