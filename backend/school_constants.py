"""
Shared constants used across agents. One source of truth for things like
class ordering — fixing it here fixes it everywhere.
"""

from pathlib import Path

# Where the editable source CSVs live. Backend re-writes these whenever a
# student or teacher record changes, so the files always reflect the DB.
DATA_DIR       = Path(__file__).resolve().parent.parent / "data"
STUDENTS_CSV   = DATA_DIR / "seed_students.csv"
TEACHERS_CSV   = DATA_DIR / "teachers.csv"
# Registrar's archive — every student that has ever existed in the
# system, including alumni and inactive ones. Read-only by design;
# the records agent re-writes it on every student change.
RECORDS_CSV    = DATA_DIR / "students_master.csv"

SCHOOL_NAME    = "Sage"
SCHOOL_ADDRESS = "Set school address in school_constants.py"
SCHOOL_PHONE   = "Set school phone in school_constants.py"

# Classes in display order. KG1 first, Class 10 last.
# Lexicographic sort would put "10" before "2", which is wrong — always
# sort with class_sort_key().
CLASS_ORDER = ["KG1", "KG2", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]


def class_sort_key(c: str) -> int:
    """Use as a sort key so KG1, KG2, 1, 2, ..., 10 stay in school order."""
    try:
        return CLASS_ORDER.index(c)
    except ValueError:
        return len(CLASS_ORDER)


SUBJECTS = ["English", "Hindi", "Math", "Science", "Social"]

EXPENSE_CATEGORIES = ["salary", "utilities", "supplies",
                       "maintenance", "transport", "other"]

PAYMENT_MODES = ("cash", "bank")


def month_bounds(d):
    """First day of d's month and first day of the next month.

    Use as a portable `date >= start AND date < nxt` filter instead of
    SQLite-only strftime("%Y-%m", ...), so the same query runs on Postgres.
    """
    start = d.replace(day=1)
    if start.month == 12:
        nxt = start.replace(year=start.year + 1, month=1)
    else:
        nxt = start.replace(month=start.month + 1)
    return start, nxt
