"""Pytest fixtures for the Tender Hands backend test suite."""

import pytest
from app import create_app
from app.config import TestingConfig
from app.extensions import db as _db
from app.models.user import User
from app.models.charity import Charity
from app.models.donation import Donation, RecurringDonation
from app.models.charity import ImpactStory, Beneficiary, InventoryItem
from datetime import date


# ---------------------------------------------------------------------------
# A config with a long-enough JWT secret so PyJWT doesn't warn
# ---------------------------------------------------------------------------

class _TestConfig(TestingConfig):
    JWT_SECRET_KEY = "test-secret-key-long-enough-32-bytes-ok"
    SECRET_KEY = "test-flask-secret-key-long-enough"


@pytest.fixture(scope="session")
def app():
    """Create application with in-memory SQLite for the test session."""
    application = create_app(_TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function", autouse=True)
def db(app):
    """Yield the db extension and wipe all tables after each test."""
    with app.app_context():
        yield _db
        # Truncate in reverse dependency order to avoid FK constraint errors
        _db.session.remove()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


# ---- User factory fixtures ----

@pytest.fixture
def admin_user(db, app):
    with app.app_context():
        user = User(full_name="Admin", email="admin@test.com", phone="+254700000099", role="admin")
        user.set_password("Admin@1234!")
        db.session.add(user)
        db.session.commit()
        return db.session.get(User, user.id)


@pytest.fixture
def donor_user(db, app):
    with app.app_context():
        user = User(full_name="Donor", email="donor@test.com", phone="+254722000099", role="donor")
        user.set_password("Donor@1234!")
        db.session.add(user)
        db.session.commit()
        return db.session.get(User, user.id)


@pytest.fixture
def charity_user(db, app):
    with app.app_context():
        user = User(full_name="Owner", email="owner@test.com", phone="+254711000099", role="charity")
        user.set_password("Owner@1234!")
        db.session.add(user)
        db.session.commit()
        return db.session.get(User, user.id)


# ---- Approved charity fixture ----

@pytest.fixture
def approved_charity(db, app, charity_user):
    with app.app_context():
        charity = Charity(
            slug="test-charity",
            name="Test Charity",
            category="Education",
            location="Nairobi",
            description="A test charity for unit tests with enough description text.",
            goal_amount=500_000,
            owner_id=charity_user.id,
            status="approved",
        )
        db.session.add(charity)
        db.session.commit()
        return db.session.get(Charity, charity.id)


# ---- Token helpers ----

def _get_tokens(client, email, password):
    resp = client.post(
        "/api/auth/login",
        json={"identifier": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.get_json()}"
    data = resp.get_json()
    return data["data"]["access_token"], data["data"]["refresh_token"]


@pytest.fixture
def donor_tokens(client, donor_user):
    return _get_tokens(client, "donor@test.com", "Donor@1234!")


@pytest.fixture
def admin_tokens(client, admin_user):
    return _get_tokens(client, "admin@test.com", "Admin@1234!")


@pytest.fixture
def charity_tokens(client, charity_user):
    return _get_tokens(client, "owner@test.com", "Owner@1234!")
