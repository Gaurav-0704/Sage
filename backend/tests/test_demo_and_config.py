"""
Demo seeder + config settings tests.

Locks the seeder (incl. the User status-kwarg regression) and the config
profile read/write + integration status.
"""

import pytest

import models
import demo_seed
from agents import config_agent


class TestDemoSeed:
    def test_seeds_then_idempotent(self, db):
        assert demo_seed.seed_demo(db) is True
        assert db.query(models.Student).count() == 10
        assert db.query(models.Teacher).count() == 2
        # teacher/student/parent logins exist
        for email in ("teacher1@sage.school", "student1@sage.school", "parent1@sage.school"):
            assert db.query(models.User).filter(models.User.email == email).first() is not None
        # linked + graded artifacts present
        assert db.query(models.ParentLink).filter(models.ParentLink.status == "approved").count() == 1
        assert db.query(models.AssignmentSubmission).filter(
            models.AssignmentSubmission.status == "graded").count() == 1
        assert db.query(models.Announcement).count() == 2
        # running again does nothing
        assert demo_seed.seed_demo(db) is False
        assert db.query(models.Student).count() == 10


class TestConfig:
    def test_profile_defaults_then_override(self, db):
        # default when unset
        assert config_agent.get_setting(db, "school_name") == config_agent.PROFILE_DEFAULTS["school_name"]
        # write + read back
        db.add(models.Setting(key="school_name", value="My School"))
        db.commit()
        assert config_agent.get_setting(db, "school_name") == "My School"

    def test_integration_status_shape(self):
        status = config_agent._integration_status()
        assert set(status.keys()) == {"ai", "email", "payments"}
        for v in status.values():
            assert "configured" in v and "env" in v
