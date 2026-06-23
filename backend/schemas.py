"""Pydantic schemas — v0.5."""

from datetime import date as Date, datetime  # noqa: F401
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict


# ---------------- USERS / AUTH ---------------- #

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    status: str
    can_do_front_office: bool


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class SignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str                          # staff | teacher | student | parent
    # Role-specific extras
    admission_no: Optional[str] = None       # students + parents (child)
    employee_id: Optional[str] = None        # teachers
    subject: Optional[str] = None            # teachers
    classes_taught: Optional[str] = None     # teachers ("5,6,7")
    qualification: Optional[str] = None      # teachers
    phone: Optional[str] = None              # teachers; parents (verification)


class ParentClaimIn(BaseModel):
    admission_no: str
    phone: str                               # must match the student's phone on record


class ParentChildOut(BaseModel):
    student_id: int
    admission_no: str
    name: str
    student_class: str
    section: Optional[str]
    link_status: str


class ParentLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    parent_user_id: int
    student_id: int
    status: str
    # enriched
    parent_name: Optional[str] = None
    parent_email: Optional[str] = None
    student_name: Optional[str] = None
    admission_no: Optional[str] = None


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    email: EmailStr
    code: str
    new_password: str


class ApprovalAction(BaseModel):
    can_do_front_office: Optional[bool] = None


# ---------------- STUDENTS ---------------- #

class StudentCreate(BaseModel):
    admission_no: str
    name: str
    aadhaar: Optional[str] = None
    dob: Optional[Date] = None
    gender: Optional[str] = None
    student_class: str
    section: Optional[str] = None
    parent_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    last_year_dues: float = 0
    admission_date: Optional[Date] = None


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    aadhaar: Optional[str] = None
    dob: Optional[Date] = None
    gender: Optional[str] = None
    student_class: Optional[str] = None
    section: Optional[str] = None
    parent_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    last_year_dues: Optional[float] = None
    status: Optional[str] = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    admission_no: str
    name: str
    aadhaar: Optional[str]
    dob: Optional[Date]
    gender: Optional[str]
    student_class: str
    section: Optional[str]
    parent_name: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    photo_url: Optional[str]
    last_year_dues: float
    status: str
    admission_date: Optional[Date]


class StudentDetailOut(StudentOut):
    total_fee: float
    paid_amount: float
    due_amount: float
    payments: List["PaymentOut"] = []


class StudentRosterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    student_class: str
    section: Optional[str]


class StudentProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    student_class: str
    section: Optional[str]
    parent_name: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    photo_url: Optional[str]


class ClassSummary(BaseModel):
    student_class: str
    count: int


# ---------------- TEACHERS ---------------- #

class TeacherCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    employee_id: str
    subject: Optional[str] = None
    classes_taught: Optional[str] = None
    qualification: Optional[str] = None
    phone: Optional[str] = None
    can_do_front_office: bool = False


class TeacherUpdate(BaseModel):
    subject: Optional[str] = None
    classes_taught: Optional[str] = None
    qualification: Optional[str] = None
    phone: Optional[str] = None
    can_do_front_office: Optional[bool] = None
    status: Optional[str] = None  # active | disabled


class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    employee_id: str
    name: str                  # joined from User
    email: str                 # joined from User
    role: str = "teacher"
    status: str = "active"
    can_do_front_office: bool = False
    subject: Optional[str]
    classes_taught: Optional[str]
    qualification: Optional[str]
    phone: Optional[str]
    joined_date: Optional[Date]
    photo_url: Optional[str]


# ---------------- ASSIGNMENTS ---------------- #

class AssignmentCreate(BaseModel):
    student_class: str
    section: Optional[str] = None
    subject: str
    title: str
    description: Optional[str] = None
    due_date: Optional[Date] = None
    max_marks: float = 10


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[Date] = None
    max_marks: Optional[float] = None
    section: Optional[str] = None


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    teacher_id: int
    teacher_name: Optional[str] = None
    student_class: str
    section: Optional[str]
    subject: str
    title: str
    description: Optional[str]
    due_date: Optional[Date]
    max_marks: float
    created_at: Optional[datetime]


# ---------------- ATTENDANCE ---------------- #

ATTENDANCE_STATUSES = ("present", "absent", "late", "leave")


class AttendanceMarkRow(BaseModel):
    student_id: int
    status: str


class AttendanceMarkIn(BaseModel):
    student_class: str
    section: Optional[str] = None
    date: Optional[Date] = None         # defaults to today server-side
    period: int = 0                     # 0 = whole-day
    rows: List[AttendanceMarkRow]


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    date: Date
    period: int
    status: str


class AttendanceClassRow(BaseModel):
    """Roster row for the marking screen — status is None if not yet marked."""
    student_id: int
    name: str
    section: Optional[str]
    status: Optional[str] = None


class AttendanceSummaryRow(BaseModel):
    student_id: int
    name: str
    section: Optional[str] = None
    total: int
    present: int
    absent: int
    late: int
    leave: int
    percentage: float                   # present+late counted as attended


class StudentAttendanceOut(BaseModel):
    total: int
    present: int
    absent: int
    late: int
    leave: int
    percentage: float
    records: List[AttendanceOut]


# ---------------- TIMETABLE ---------------- #

TIMETABLE_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


class TimetableEntryCreate(BaseModel):
    student_class: str
    section: str = "A"
    day: str                            # Mon..Sat
    period: int                         # 1..N
    subject: str
    teacher_id: Optional[int] = None
    room: Optional[str] = None
    academic_year: Optional[str] = None


class TimetableEntryUpdate(BaseModel):
    day: Optional[str] = None
    period: Optional[int] = None
    subject: Optional[str] = None
    teacher_id: Optional[int] = None
    room: Optional[str] = None


class TimetableEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_class: str
    section: str
    day: str
    period: int
    subject: str
    teacher_id: Optional[int]
    teacher_name: Optional[str] = None
    room: Optional[str]
    academic_year: Optional[str]


# ---------------- FEES ---------------- #

class FeeStructureCreate(BaseModel):
    student_class: str
    academic_year: str
    tuition_fee: float = 0
    transport_fee: float = 0
    books_fee: float = 0
    uniform_fee: float = 0
    other_fee: float = 0


class FeeStructureOut(FeeStructureCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class FeeCreate(BaseModel):
    student_id: int
    academic_year: str
    total_fee: float
    due_date: Optional[str] = None


class FeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    academic_year: str
    total_fee: float
    paid_amount: float
    due_amount: float
    due_date: Optional[str]


class PaymentCreate(BaseModel):
    student_id: int
    amount: float
    date: Optional[Date] = None
    mode: str
    fee_head: Optional[str] = None
    reference: Optional[str] = None
    note: Optional[str] = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    amount: float
    date: Date
    mode: str
    fee_head: Optional[str]
    reference: Optional[str]
    note: Optional[str]


# ---------------- EXPENSES ---------------- #

class ExpenseCreate(BaseModel):
    title: str
    amount: float
    category: str
    paid_from: str
    date: Optional[Date] = None
    note: Optional[str] = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    amount: float
    category: str
    paid_from: str
    date: Date
    note: Optional[str]


# ---------------- FINANCE ---------------- #

class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    opening_balance: float
    balance: float


class FinanceSummary(BaseModel):
    cash: AccountOut
    bank: AccountOut
    total_balance: float
    total_collected_today: float
    total_collected_month: float
    total_expense_today: float
    total_expense_month: float


class AccountUpdate(BaseModel):
    opening_balance: float


# ---------------- EXAMS / MARKS ---------------- #

class ExamCreate(BaseModel):
    name: str
    academic_year: str
    student_class: str
    date: Optional[Date] = None


class ExamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    academic_year: str
    student_class: str
    date: Optional[Date]


class MarkIn(BaseModel):
    student_id: int
    subject: str
    marks_obtained: float
    max_marks: float = 100


class MarksBulkIn(BaseModel):
    exam_id: int
    rows: List[MarkIn]


class MarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    exam_id: int
    subject: str
    max_marks: float
    marks_obtained: float


class StudentExamReport(BaseModel):
    exam_id: int
    exam_name: str
    academic_year: str
    date: Optional[Date]
    total_obtained: float
    total_max: float
    percentage: float
    grade: str
    subjects: List[MarkOut]


class StudentPerformance(BaseModel):
    student_id: int
    exam_id: Optional[int]
    exam_name: Optional[str]
    student_percentage: Optional[float]
    class_average: Optional[float]
    rank: Optional[int]
    class_size: Optional[int]
    subject_breakdown: List[dict]


# ---------------- TILES ---------------- #

class TileCreate(BaseModel):
    label: str
    kind: str
    category: Optional[str] = None
    fee_head: Optional[str] = None
    icon: Optional[str] = "💰"
    color: Optional[str] = "#d4a574"
    sort_order: int = 0
    active: bool = True


class TileUpdate(BaseModel):
    label: Optional[str] = None
    kind: Optional[str] = None
    category: Optional[str] = None
    fee_head: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None
    active: Optional[bool] = None


class TileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    label: str
    kind: str
    category: Optional[str]
    fee_head: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    sort_order: int
    active: bool


# ---------------- DASHBOARD / REPORTS ---------------- #

class DashboardOut(BaseModel):
    total_students: int
    active_students: int
    total_fee_value: float
    total_collected: float
    total_due: float
    total_expense: float
    cash_balance: float
    bank_balance: float
    net: float
    collected_today: float
    collected_this_month: float


class DailyReportRow(BaseModel):
    date: Date
    collected: float
    expense: float
    net: float


class MonthlyReportRow(BaseModel):
    month: str
    collected: float
    expense: float
    net: float


class YearlyReport(BaseModel):
    academic_year: str
    total_fee_value: float
    total_collected: float
    total_due: float
    total_expense: float
    net: float


# ---------------- SELF DASHBOARDS ---------------- #

class TeacherDashboardOut(BaseModel):
    classes: List[str]
    students_count: int
    assignments_count: int
    upcoming_due: List[AssignmentOut]


class StudentDashboardOut(BaseModel):
    name: str
    student_class: str
    section: Optional[str]
    upcoming_assignments: List[AssignmentOut]
    recent_marks: List[StudentExamReport]
    next_exam: Optional[ExamOut]


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    to_email: str
    subject: str
    body: str
    kind: str
    delivered: bool
    created_at: datetime


# ---------------- AUDIT ---------------- #

class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: Optional[int]
    user_name: Optional[str]
    user_role: Optional[str]
    method: str
    path: str
    status_code: Optional[int]
    summary: Optional[str]
    details: Optional[str]
    ip: Optional[str]
    created_at: datetime


# ---------------- SCANNER ---------------- #

class ScannerRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    started_at: datetime
    finished_at: Optional[datetime]
    triggered_by: str
    status: str
    issues_count: int
    summary: Optional[str]
    findings: Optional[str]


# ---------------- AI ---------------- #

class AIConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    created_at: datetime


class AIMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conversation_id: int
    role: str
    content: str
    actions: Optional[str]
    executed: bool
    created_at: datetime


class AIChatIn(BaseModel):
    conversation_id: Optional[int] = None
    message: str


class AIExecuteIn(BaseModel):
    conversation_id: int
    message_id: int


class AIInsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category: str
    severity: str
    title: str
    body: str
    action_hint: Optional[str]
    generated_at: datetime
    dismissed: bool


# ---------------- AT-RISK ---------------- #

class AtRiskStudent(BaseModel):
    id: int
    admission_no: str
    name: str
    student_class: str
    section: Optional[str]
    parent_name: Optional[str]
    phone: Optional[str]
    due: float
    days_since_payment: Optional[int]
    risk_score: int          # 0-100
    risk_level: str          # low | medium | high | critical


StudentDetailOut.model_rebuild()
TeacherDashboardOut.model_rebuild()
StudentDashboardOut.model_rebuild()
