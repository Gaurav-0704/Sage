"""
TIER 2 — Razorpay signature verification + record_payment integration.

Signature verification is pure HMAC, so we test it deterministically by
patching the key. record_payment is tested for correct due settlement +
reference capture (the path the verify endpoint uses).
"""

import hashlib
import hmac

import pytest

import models
import razorpay_client
from agents import fees_agent


class TestSignature:
    def test_valid_signature_accepts(self, monkeypatch):
        monkeypatch.setattr(razorpay_client, "KEY_SECRET", "secret123")
        order_id, payment_id = "order_X", "pay_Y"
        sig = hmac.new(b"secret123", f"{order_id}|{payment_id}".encode(),
                       hashlib.sha256).hexdigest()
        assert razorpay_client.verify_signature(order_id, payment_id, sig) is True

    def test_tampered_signature_rejected(self, monkeypatch):
        monkeypatch.setattr(razorpay_client, "KEY_SECRET", "secret123")
        assert razorpay_client.verify_signature("order_X", "pay_Y", "deadbeef") is False

    def test_no_secret_rejects(self, monkeypatch):
        monkeypatch.setattr(razorpay_client, "KEY_SECRET", None)
        assert razorpay_client.verify_signature("a", "b", "c") is False

    def test_enabled_reflects_keys(self, monkeypatch):
        monkeypatch.setattr(razorpay_client, "KEY_ID", "rzp_test_1")
        monkeypatch.setattr(razorpay_client, "KEY_SECRET", "s")
        assert razorpay_client.enabled() is True
        monkeypatch.setattr(razorpay_client, "KEY_ID", None)
        assert razorpay_client.enabled() is False


class TestRecordPayment:
    def test_settles_dues_and_records_reference(self, db):
        s = models.Student(admission_no="P1", name="Pay", student_class="5",
                           status="active", last_year_dues=0)
        db.add(s); db.commit(); db.refresh(s)
        db.add(models.Fee(student_id=s.id, academic_year="2025-26",
                          total_fee=1000, paid_amount=0, due_amount=1000))
        db.commit()

        p = fees_agent.record_payment(db, s, amount=600, mode="bank",
                                      reference="pay_abc", note="Razorpay online")
        assert p.amount == 600
        assert p.reference == "pay_abc"
        fee = db.query(models.Fee).filter(models.Fee.student_id == s.id).first()
        assert fee.due_amount == 400
        assert fee.paid_amount == 600

    def test_can_pay_for_rules(self, db):
        s = models.Student(admission_no="P2", name="Kid", student_class="5",
                           status="active", last_year_dues=0)
        db.add(s); db.commit(); db.refresh(s)

        owner = models.User(name="O", email="o@t.com", password="x",
                            role="owner", status="active")
        parent = models.User(name="P", email="p@t.com", password="x",
                             role="parent", status="active")
        db.add_all([owner, parent]); db.commit()

        assert fees_agent._can_pay_for(db, owner, s) is True
        assert fees_agent._can_pay_for(db, parent, s) is False   # no link yet
        db.add(models.ParentLink(parent_user_id=parent.id, student_id=s.id,
                                 status="approved"))
        db.commit()
        assert fees_agent._can_pay_for(db, parent, s) is True
