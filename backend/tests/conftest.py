"""
Shared pytest fixtures for Sage backend tests.
Uses an in-memory SQLite database — each test gets a fresh one.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
import models
import auth


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def owner_user(db):
    u = models.User(
        name="Test Owner", email="owner@test.com",
        password=auth.hash_password("test123"),
        role="owner", status="active",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def student(db):
    s = models.Student(
        admission_no="TEST001", name="Arjun Kumar",
        student_class="5", section="A",
        parent_name="Suresh Kumar", phone="9876543210",
        last_year_dues=0, status="active",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@pytest.fixture()
def fee_structure(db):
    fs = models.FeeStructure(
        student_class="5", academic_year="2025-26",
        tuition_fee=12000, transport_fee=3000,
        books_fee=2000, uniform_fee=1500, other_fee=500,
    )
    db.add(fs)
    db.commit()
    db.refresh(fs)
    return fs
