"""
ORM models — Nagarjuna High School ERP, v0.5.

    users, password_reset_codes, notifications -> Auth Agent
    students                                   -> Students Agent
    teachers                                   -> Teachers Agent
    assignments                                -> Assignments Agent
    fee_structures, fees, payments             -> Fees Agent
    expenses                                   -> Expenses Agent
    accounts                                   -> Finance Agent
    exams, marks                               -> Exams Agent
    tiles                                      -> Tiles Agent
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # owner | staff | teacher | student
    status = Column(String, default="active")  # active | pending | disabled
    can_do_front_office = Column(Boolean, default=False)  # for teachers
    created_at = Column(DateTime, default=datetime.utcnow)


class PasswordResetCode(Base):
    """6-digit codes emailed for password reset / 2-factor verification."""
    __tablename__ = "password_reset_codes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)


class Notification(Base):
    """All system-sent notifications. Owner can audit them."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    to_email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    kind = Column(String, default="email")
    delivered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    admission_no = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    aadhaar = Column(String, index=True)
    dob = Column(Date)
    gender = Column(String)
    student_class = Column(String, nullable=False)
    section = Column(String)
    parent_name = Column(String)
    phone = Column(String)
    address = Column(Text)
    photo_url = Column(String)
    last_year_dues = Column(Float, default=0)
    status = Column(String, default="active")
    admission_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    fees = relationship("Fee", back_populates="student", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="student", cascade="all, delete-orphan")


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    employee_id = Column(String, unique=True, nullable=False, index=True)
    subject = Column(String)
    classes_taught = Column(String)   # comma-separated: "5,6,7"
    qualification = Column(String)
    phone = Column(String)
    joined_date = Column(Date, default=date.today)
    photo_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    student_class = Column(String, nullable=False)
    section = Column(String)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    due_date = Column(Date)
    max_marks = Column(Float, default=10)
    created_at = Column(DateTime, default=datetime.utcnow)


class FeeStructure(Base):
    __tablename__ = "fee_structures"

    id = Column(Integer, primary_key=True)
    student_class = Column(String, nullable=False)
    academic_year = Column(String, nullable=False)
    tuition_fee = Column(Float, default=0)
    transport_fee = Column(Float, default=0)
    books_fee = Column(Float, default=0)
    uniform_fee = Column(Float, default=0)
    other_fee = Column(Float, default=0)


class Fee(Base):
    __tablename__ = "fees"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    academic_year = Column(String, nullable=False)
    total_fee = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0)
    due_amount = Column(Float, nullable=False)
    due_date = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="fees")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    mode = Column(String, nullable=False)
    fee_head = Column(String)
    reference = Column(String)
    note = Column(String)
    received_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="payments")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    paid_from = Column(String, nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    note = Column(String)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    opening_balance = Column(Float, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    academic_year = Column(String, nullable=False)
    student_class = Column(String, nullable=False)
    date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

    marks = relationship("Mark", back_populates="exam", cascade="all, delete-orphan")


class Mark(Base):
    __tablename__ = "marks"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    subject = Column(String, nullable=False)
    max_marks = Column(Float, default=100)
    marks_obtained = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    exam = relationship("Exam", back_populates="marks")


class AuditLog(Base):
    """Records every state-changing action by any user."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user_name = Column(String)
    user_role = Column(String)
    method = Column(String, nullable=False)             # POST | PUT | DELETE | PATCH
    path = Column(String, nullable=False)
    status_code = Column(Integer)
    summary = Column(String)                            # human-readable, e.g. "Added student"
    details = Column(Text)                              # optional JSON snapshot
    ip = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ScannerRun(Base):
    """One row per scan executed by the Scanner agent."""
    __tablename__ = "scanner_runs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    triggered_by = Column(String, default="schedule")   # schedule | manual
    status = Column(String, default="running")          # running | ok | issues | failed
    issues_count = Column(Integer, default=0)
    summary = Column(Text)
    findings = Column(Text)                             # JSON array


class AIConversation(Base):
    """Chat history between an Owner and the AI assistant."""
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New conversation")
    created_at = Column(DateTime, default=datetime.utcnow)


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id"), nullable=False)
    role = Column(String, nullable=False)               # user | assistant
    content = Column(Text, nullable=False)
    actions = Column(Text)                               # JSON: proposed tool calls
    executed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Tile(Base):
    __tablename__ = "tiles"

    id = Column(Integer, primary_key=True)
    label = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    category = Column(String)
    fee_head = Column(String)
    icon = Column(String, default="💰")
    color = Column(String, default="#d4a574")
    sort_order = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AIInsight(Base):
    """Proactive AI-generated observations about school health, written nightly."""
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True)
    category = Column(String, nullable=False)   # finance | fees | academic | operations
    severity = Column(String, default="info")   # info | warning | critical
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    action_hint = Column(String)                # suggested follow-up question for assistant
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    dismissed = Column(Boolean, default=False)


class TeacherClass(Base):
    """Normalised teacher ↔ class mapping (replaces comma-separated classes_taught)."""
    __tablename__ = "teacher_classes"

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, index=True)
    student_class = Column(String, nullable=False)
