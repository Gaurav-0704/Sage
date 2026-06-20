"""
Agent modules — Sage v1.0. Each agent owns a single domain:

    auth_agent      - login, JWT, user management
    students_agent  - student profiles + financial summary
    fees_agent      - fee structures, bills, payments
    finance_agent   - cash + bank account balances (live recompute)
    expenses_agent  - school expenses by category
    reports_agent   - daily / monthly / yearly aggregates + dashboard + at-risk
    tiles_agent     - front-office quick-action tiles
    exams_agent     - exams + marks
    teachers_agent  - teacher records
    assignments_agent - assignments per class/subject
    teacher_self_agent - teacher dashboard
    student_self_agent - student dashboard
    audit_agent     - searchable audit log
    scanner_agent   - nightly self-diagnostics
    ai_agent        - Claude assistant (propose + approve pattern) + SSE streaming
    records_agent   - bulk records export
    insights_agent  - proactive AI-generated school health insights
"""
