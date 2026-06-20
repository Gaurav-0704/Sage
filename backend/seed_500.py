"""
Sage — 500-student seed script.

Generates realistic data:
  - 500 students spread across KG1–10 with Indian names
  - 12 teachers (2 per section of classes)
  - Fee structures for all classes (2025-26)
  - Fee bills applied to all active students
  - Partial and full payments with realistic variation
  - 6 months of expenses across all categories
  - 3 exams per class with marks
  - Assignments from each teacher

Run: python seed_500.py
Idempotent — safe to run multiple times (checks existing data first).
"""

import random
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, engine, Base
import models
import auth

Base.metadata.create_all(bind=engine)

rng = random.Random(42)   # fixed seed for reproducibility

# ---------------------------------------------------------------------------
# Name pools — common South Indian / Indian names
# ---------------------------------------------------------------------------

FIRST_NAMES_M = [
    "Arjun", "Rahul", "Vikram", "Aditya", "Karthik", "Suresh", "Ravi", "Deepak",
    "Akash", "Nikhil", "Sai", "Rohit", "Pranav", "Harish", "Manoj", "Venkat",
    "Gopal", "Krishna", "Surya", "Naveen", "Ajay", "Vijay", "Rajesh", "Sandeep",
    "Sravan", "Lokesh", "Tarun", "Charan", "Pavan", "Hemanth", "Dinesh", "Girish",
    "Anand", "Bhaskar", "Chandra", "Durgesh", "Eshan", "Farhan", "Gaurav", "Hemant",
]
FIRST_NAMES_F = [
    "Priya", "Deepika", "Anjali", "Sneha", "Pooja", "Divya", "Kavya", "Meera",
    "Swathi", "Lakshmi", "Sravani", "Nandini", "Keerthi", "Madhuri", "Ramya",
    "Bhavana", "Sirisha", "Tejaswi", "Usha", "Vaishali", "Rani", "Padmaja",
    "Haritha", "Indira", "Jyothi", "Archana", "Bindu", "Chitra", "Devi", "Eesha",
    "Falguni", "Gayatri", "Hema", "Ishita", "Jasmine", "Kalyani", "Latha",
]
LAST_NAMES = [
    "Reddy", "Sharma", "Kumar", "Rao", "Singh", "Patel", "Naidu", "Varma",
    "Chowdhury", "Krishnamurthy", "Venkatesh", "Subramaniam", "Iyer", "Pillai",
    "Nair", "Menon", "Joshi", "Gupta", "Mishra", "Agarwal", "Bose", "Das",
    "Ghosh", "Banerjee", "Chatterjee", "Mukherjee", "Sen", "Dutta", "Roy", "Paul",
]
PARENT_PREFIXES = ["Mr.", "Mrs.", "Sri", "Smt."]
ADDRESSES = [
    "12 Gandhi Nagar, Hyderabad",
    "45 Jubilee Hills, Hyderabad",
    "78 Banjara Hills, Hyderabad",
    "23 KPHB Colony, Hyderabad",
    "56 Kukatpally, Hyderabad",
    "89 Miyapur, Hyderabad",
    "34 Dilsukhnagar, Hyderabad",
    "67 Ameerpet, Hyderabad",
    "11 Secunderabad, Telangana",
    "99 LB Nagar, Hyderabad",
    "44 Mehdipatnam, Hyderabad",
    "22 Tolichowki, Hyderabad",
]

CLASSES = ["KG1", "KG2", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
SECTIONS = ["A", "B"]

FEE_STRUCTURES = {
    "KG1":  {"tuition": 8000,  "transport": 2500, "books": 1500, "uniform": 1000, "other": 500},
    "KG2":  {"tuition": 8500,  "transport": 2500, "books": 1500, "uniform": 1000, "other": 500},
    "1":    {"tuition": 10000, "transport": 3000, "books": 2000, "uniform": 1200, "other": 500},
    "2":    {"tuition": 10000, "transport": 3000, "books": 2000, "uniform": 1200, "other": 500},
    "3":    {"tuition": 11000, "transport": 3000, "books": 2200, "uniform": 1200, "other": 600},
    "4":    {"tuition": 11000, "transport": 3000, "books": 2200, "uniform": 1200, "other": 600},
    "5":    {"tuition": 12000, "transport": 3000, "books": 2500, "uniform": 1300, "other": 700},
    "6":    {"tuition": 13000, "transport": 3500, "books": 2800, "uniform": 1300, "other": 700},
    "7":    {"tuition": 14000, "transport": 3500, "books": 3000, "uniform": 1400, "other": 800},
    "8":    {"tuition": 15000, "transport": 3500, "books": 3200, "uniform": 1400, "other": 800},
    "9":    {"tuition": 18000, "transport": 4000, "books": 3500, "uniform": 1500, "other": 1000},
    "10":   {"tuition": 20000, "transport": 4000, "books": 4000, "uniform": 1500, "other": 1000},
}

SUBJECTS = {
    "KG1": ["English", "Math", "EVS"], "KG2": ["English", "Math", "EVS"],
    "1":   ["English", "Math", "Telugu", "EVS"],
    "2":   ["English", "Math", "Telugu", "EVS"],
    "3":   ["English", "Math", "Telugu", "Science"],
    "4":   ["English", "Math", "Telugu", "Science"],
    "5":   ["English", "Math", "Telugu", "Science", "Social"],
    "6":   ["English", "Math", "Telugu", "Science", "Social"],
    "7":   ["English", "Math", "Telugu", "Physics", "Chemistry", "Biology", "Social"],
    "8":   ["English", "Math", "Telugu", "Physics", "Chemistry", "Biology", "Social"],
    "9":   ["English", "Math", "Telugu", "Physics", "Chemistry", "Biology", "Social", "Hindi"],
    "10":  ["English", "Math", "Telugu", "Physics", "Chemistry", "Biology", "Social", "Hindi"],
}

EXPENSE_CATEGORIES = ["salary", "utilities", "supplies", "maintenance", "transport", "other"]
EXPENSE_TITLES = {
    "salary":      ["Teacher salary", "Support staff salary", "Security salary", "Admin salary"],
    "utilities":   ["Electricity bill", "Water bill", "Internet charges", "Phone bill"],
    "supplies":    ["Stationery", "Chalk & boards", "Art supplies", "Lab materials"],
    "maintenance": ["Building repair", "Plumbing work", "Electrical repair", "AC servicing"],
    "transport":   ["Bus fuel", "Bus maintenance", "Driver allowance", "Van service"],
    "other":       ["Printing charges", "Event expenses", "Sports equipment", "Library books"],
}


def _name(gender):
    if gender == "M":
        return rng.choice(FIRST_NAMES_M) + " " + rng.choice(LAST_NAMES)
    return rng.choice(FIRST_NAMES_F) + " " + rng.choice(LAST_NAMES)


def _phone():
    return "9" + str(rng.randint(100000000, 999999999))


def _aadhaar():
    return str(rng.randint(100000000000, 999999999999))


def main():
    db = SessionLocal()
    try:
        existing = db.query(models.Student).count()
        if existing >= 400:
            print(f"Already have {existing} students — skipping seed.")
            return

        print("Seeding Sage with 500 students...")

        # ------------------------------------------------------------------ #
        # 1. Fee structures
        # ------------------------------------------------------------------ #
        print("  Creating fee structures...")
        fs_map = {}
        for cls, fees in FEE_STRUCTURES.items():
            existing_fs = db.query(models.FeeStructure).filter(
                models.FeeStructure.student_class == cls,
                models.FeeStructure.academic_year == "2025-26",
            ).first()
            if existing_fs:
                fs_map[cls] = existing_fs
                continue
            fs = models.FeeStructure(
                student_class=cls, academic_year="2025-26",
                tuition_fee=fees["tuition"], transport_fee=fees["transport"],
                books_fee=fees["books"], uniform_fee=fees["uniform"], other_fee=fees["other"],
            )
            db.add(fs)
            fs_map[cls] = fs
        db.commit()

        # ------------------------------------------------------------------ #
        # 2. Teachers (12 teachers)
        # ------------------------------------------------------------------ #
        print("  Creating teachers...")
        teacher_records = []
        teacher_subjects = [
            ("English", "1,2,3,4,5"),
            ("Mathematics", "6,7,8,9,10"),
            ("Telugu", "1,2,3,4,5,6"),
            ("Science", "5,6,7,8"),
            ("Physics", "9,10"),
            ("Chemistry", "9,10"),
            ("Biology", "9,10"),
            ("Social Studies", "6,7,8,9,10"),
            ("Hindi", "8,9,10"),
            ("EVS", "KG1,KG2,1,2"),
            ("Art & Craft", "KG1,KG2,1,2,3,4"),
            ("Physical Education", "1,2,3,4,5,6,7,8,9,10"),
        ]
        for i, (subj, classes) in enumerate(teacher_subjects):
            emp_id = f"EMP{i+1:03d}"
            if db.query(models.Teacher).filter(models.Teacher.employee_id == emp_id).first():
                t = db.query(models.Teacher).filter(models.Teacher.employee_id == emp_id).first()
                teacher_records.append(t)
                continue
            gender = rng.choice(["M", "F"])
            tname = _name(gender)
            email = f"teacher{i+1}@sage.school"
            if db.query(models.User).filter(models.User.email == email).first():
                u = db.query(models.User).filter(models.User.email == email).first()
            else:
                u = models.User(
                    name=tname, email=email,
                    password=auth.hash_password("teacher123"),
                    role="teacher", status="active",
                )
                db.add(u)
                db.commit()
                db.refresh(u)
            t = models.Teacher(
                user_id=u.id, employee_id=emp_id,
                subject=subj, classes_taught=classes,
                qualification=rng.choice(["B.Ed", "M.Ed", "M.Sc B.Ed", "MA B.Ed"]),
                phone=_phone(),
                joined_date=date(2020, rng.randint(1, 12), rng.randint(1, 28)),
            )
            db.add(t)
            db.commit()
            db.refresh(t)
            teacher_records.append(t)

        # ------------------------------------------------------------------ #
        # 3. 500 students
        # ------------------------------------------------------------------ #
        print("  Creating 500 students...")
        # Distribute across classes: ~40 per class
        class_dist = []
        for cls in CLASSES:
            n = 42 if cls in ("9", "10") else 40
            class_dist.extend([cls] * n)
        rng.shuffle(class_dist)
        class_dist = class_dist[:500]

        admission_counter = db.query(models.Student).count() + 1
        students_by_class = {c: [] for c in CLASSES}

        for i, cls in enumerate(class_dist):
            gender = rng.choice(["M", "F"])
            sname  = _name(gender)
            pname  = rng.choice(PARENT_PREFIXES) + " " + _name("M")
            section = rng.choice(SECTIONS)
            dob_year = date.today().year - (5 + CLASSES.index(cls))
            dob = date(dob_year, rng.randint(1, 12), rng.randint(1, 28))

            last_yr = rng.choice([0, 0, 0, 0, 0, 0, 0,
                                   rng.randint(500, 8000)])  # ~12% have carry-forward

            s = models.Student(
                admission_no=f"SGE{admission_counter:04d}",
                name=sname,
                aadhaar=_aadhaar() if rng.random() > 0.2 else None,
                dob=dob,
                gender=gender,
                student_class=cls,
                section=section,
                parent_name=pname,
                phone=_phone(),
                address=rng.choice(ADDRESSES),
                last_year_dues=float(last_yr),
                status=rng.choices(["active", "active", "active", "active",
                                     "active", "active", "active", "active",
                                     "active", "inactive"], k=1)[0],
                admission_date=date(2024, rng.randint(4, 6), rng.randint(1, 25)),
            )
            db.add(s)
            admission_counter += 1
            students_by_class[cls].append(s)

        db.commit()

        # ------------------------------------------------------------------ #
        # 4. Apply fee structures (bills)
        # ------------------------------------------------------------------ #
        print("  Applying fee structures...")
        for cls, fs in fs_map.items():
            total = (fs.tuition_fee + fs.transport_fee + fs.books_fee
                     + fs.uniform_fee + fs.other_fee)
            for s in students_by_class[cls]:
                if s.status != "active":
                    continue
                if db.query(models.Fee).filter(
                    models.Fee.student_id == s.id,
                    models.Fee.academic_year == "2025-26",
                ).first():
                    continue
                db.add(models.Fee(
                    student_id=s.id, academic_year="2025-26",
                    total_fee=total, paid_amount=0, due_amount=total,
                ))
        db.commit()

        # ------------------------------------------------------------------ #
        # 5. Payments — realistic variation
        # ------------------------------------------------------------------ #
        print("  Recording payments...")
        today = date.today()
        all_fees = db.query(models.Fee).all()

        for fee in all_fees:
            student = db.query(models.Student).filter(models.Student.id == fee.student_id).first()
            if not student:
                continue

            # Payment behaviour:
            # 30% pay in full immediately
            # 40% pay 50-80%
            # 20% pay 20-50%
            # 10% pay nothing (defaulters)
            r = rng.random()
            if r < 0.30:
                pay_fraction = 1.0
            elif r < 0.70:
                pay_fraction = rng.uniform(0.5, 0.9)
            elif r < 0.90:
                pay_fraction = rng.uniform(0.2, 0.5)
            else:
                pay_fraction = 0.0

            if pay_fraction == 0:
                continue

            total_to_pay = fee.total_fee * pay_fraction
            # Split into 1-3 instalments
            n_instalments = rng.choice([1, 1, 2, 3])
            splits = sorted([rng.random() for _ in range(n_instalments - 1)] + [0, 1])
            amounts = [round((splits[i+1] - splits[i]) * total_to_pay)
                       for i in range(n_instalments)]
            amounts = [a for a in amounts if a > 0]

            base_date = date(today.year, 4, 1)  # Academic year starts April
            for j, amt in enumerate(amounts):
                pay_date = base_date + timedelta(days=rng.randint(j * 30, j * 30 + 60))
                if pay_date > today:
                    pay_date = today - timedelta(days=rng.randint(1, 30))
                mode = rng.choice(["cash", "cash", "bank"])
                p = models.Payment(
                    student_id=student.id,
                    amount=float(max(1, amt)),
                    date=pay_date,
                    mode=mode,
                    fee_head=rng.choice(["Tuition", "Transport", "Books", "Uniform", "General"]),
                )
                db.add(p)
                remaining = float(max(1, amt))
                for f in db.query(models.Fee).filter(
                    models.Fee.student_id == student.id,
                    models.Fee.due_amount > 0,
                ).order_by(models.Fee.id).all():
                    if remaining <= 0:
                        break
                    applied = min(remaining, f.due_amount)
                    f.paid_amount += applied
                    f.due_amount  -= applied
                    remaining     -= applied
                if remaining > 0 and (student.last_year_dues or 0) > 0:
                    applied = min(remaining, student.last_year_dues)
                    student.last_year_dues -= applied
        db.commit()

        # ------------------------------------------------------------------ #
        # 6. Expenses — 6 months
        # ------------------------------------------------------------------ #
        print("  Recording expenses...")
        for month_offset in range(6):
            exp_date = date(today.year, max(1, today.month - month_offset), 15)
            if exp_date > today:
                exp_date = today

            # Salary — monthly
            db.add(models.Expense(
                title="Monthly teacher salaries",
                amount=float(rng.randint(180000, 220000)),
                category="salary", paid_from="bank",
                date=exp_date,
            ))
            # Support staff
            db.add(models.Expense(
                title="Support staff wages",
                amount=float(rng.randint(40000, 60000)),
                category="salary", paid_from="cash",
                date=exp_date,
            ))
            # Utilities
            for cat in ["utilities", "supplies", "maintenance"]:
                if rng.random() > 0.3:
                    title = rng.choice(EXPENSE_TITLES[cat])
                    db.add(models.Expense(
                        title=title,
                        amount=float(rng.randint(2000, 25000)),
                        category=cat,
                        paid_from=rng.choice(["cash", "bank"]),
                        date=exp_date - timedelta(days=rng.randint(0, 10)),
                    ))
        db.commit()

        # ------------------------------------------------------------------ #
        # 7. Exams + marks (3 exams per class)
        # ------------------------------------------------------------------ #
        print("  Creating exams and marks...")
        exam_names = ["Unit Test 1", "Mid-Term", "Annual Exam"]
        # Use dates that are always in the past relative to today
        exam_dates = [
            today - timedelta(days=180),
            today - timedelta(days=90),
            today - timedelta(days=30),
        ]

        for cls in CLASSES:
            subjects = SUBJECTS.get(cls, ["English", "Math"])
            cls_students = [s for s in students_by_class[cls] if s.status == "active"]
            if not cls_students:
                continue

            for ename, edate in zip(exam_names, exam_dates):
                if edate > today:
                    continue
                exam = models.Exam(
                    name=ename, academic_year="2025-26",
                    student_class=cls, date=edate,
                )
                db.add(exam)
                db.commit()
                db.refresh(exam)

                for s in cls_students:
                    for subj in subjects:
                        obtained = rng.gauss(68, 15)
                        obtained = max(10, min(100, obtained))
                        db.add(models.Mark(
                            student_id=s.id, exam_id=exam.id,
                            subject=subj, max_marks=100,
                            marks_obtained=round(obtained, 1),
                        ))
                db.commit()

        # ------------------------------------------------------------------ #
        # 8. Assignments — 3 per teacher
        # ------------------------------------------------------------------ #
        print("  Creating assignments...")
        for t in teacher_records:
            classes_list = [c.strip() for c in (t.classes_taught or "").split(",") if c.strip()]
            for cls in rng.sample(classes_list, min(2, len(classes_list))):
                subjects = SUBJECTS.get(cls, ["English"])
                subj = t.subject if t.subject in subjects else rng.choice(subjects)
                due = today + timedelta(days=rng.randint(7, 30))
                db.add(models.Assignment(
                    teacher_id=t.id,
                    student_class=cls,
                    section=rng.choice(SECTIONS),
                    subject=subj,
                    title=f"{subj} Chapter Practice - {cls}",
                    description=f"Complete exercises from the assigned chapter. Show all working.",
                    due_date=due,
                    max_marks=20,
                ))
        db.commit()

        # ------------------------------------------------------------------ #
        # Summary
        # ------------------------------------------------------------------ #
        n_students  = db.query(models.Student).count()
        n_payments  = db.query(models.Payment).count()
        n_fees      = db.query(models.Fee).count()
        n_expenses  = db.query(models.Expense).count()
        n_exams     = db.query(models.Exam).count()
        n_marks     = db.query(models.Mark).count()
        n_assign    = db.query(models.Assignment).count()

        print(f"\n  Done! Database summary:")
        print(f"    Students   : {n_students}")
        print(f"    Teachers   : {len(teacher_records)}")
        print(f"    Fee bills  : {n_fees}")
        print(f"    Payments   : {n_payments}")
        print(f"    Expenses   : {n_expenses}")
        print(f"    Exams      : {n_exams}")
        print(f"    Marks      : {n_marks}")
        print(f"    Assignments: {n_assign}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
