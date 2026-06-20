"""
Agent modules. Each agent owns a single domain:

    auth_agent      - login, JWT, user management
    students_agent  - student profiles + financial summary
    fees_agent      - fee structures, bills, payments
    finance_agent   - cash + bank account balances (live recompute)
    expenses_agent  - school expenses by category
    reports_agent   - daily / monthly / yearly aggregates + dashboard
"""
