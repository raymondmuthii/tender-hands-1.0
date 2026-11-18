"""Tests for recurring donations scheduling (POST /api/recurring/run-due)."""

import calendar
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.models.donation import Donation, RecurringDonation

CRON_SECRET = "test-cron-secret-value"
CRON_HEADERS = {"X-Cron-Secret": CRON_SECRET}

STK_OK = {"CheckoutRequestID": "ws_CO_RECURRING_1", "ResponseCode": "0"}


def _make_recurring(db, donor_user, charity, *, days_from_today=0, status="active", amount=1000):
    rec = RecurringDonation(
        user_id=donor_user.id,
        charity_id=charity.id,
        amount=amount,
        frequency="monthly",
        next_run_date=date.today() + timedelta(days=days_from_today),
        status=status,
    )
    db.session.add(rec)
    db.session.commit()
    return rec


def _one_month_later(current: date) -> date:
    year = current.year + (1 if current.month == 12 else 0)
    month = 1 if current.month == 12 else current.month + 1
    return date(year, month, min(current.day, calendar.monthrange(year, month)[1]))


class TestRunDueAuth:
    def test_missing_secret_is_rejected(self, client, db):
        resp = client.post("/api/recurring/run-due")
        assert resp.status_code == 403
        assert resp.get_json()["success"] is False

    def test_wrong_secret_is_rejected(self, client, db):
        resp = client.post(
            "/api/recurring/run-due", headers={"X-Cron-Secret": "not-the-secret"}
        )
        assert resp.status_code == 403

    def test_unconfigured_secret_is_rejected(self, client, app, monkeypatch):
        monkeypatch.setitem(app.config, "CRON_SECRET", "")
        resp = client.post("/api/recurring/run-due", headers=CRON_HEADERS)
        assert resp.status_code == 403

    def test_jwt_is_not_accepted_instead_of_secret(
        self, client, donor_user, donor_tokens
    ):
        access, _ = donor_tokens
        resp = client.post(
            "/api/recurring/run-due",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 403


class TestRunDueExecution:
    def test_no_due_donations_is_a_noop(
        self, client, db, donor_user, approved_charity
    ):
        _make_recurring(db, donor_user, approved_charity, days_from_today=10)

        resp = client.post("/api/recurring/run-due", headers=CRON_HEADERS)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["due"] == 0
        assert data["created"] == 0
        assert Donation.query.count() == 0

    def test_due_donation_is_charged_and_advanced(
        self, client, db, donor_user, approved_charity
    ):
        rec = _make_recurring(db, donor_user, approved_charity, days_from_today=0)
        expected_next = _one_month_later(date.today())

        with patch(
            "app.routes.recurring.mpesa_service.stk_push", return_value=STK_OK
        ):
            resp = client.post("/api/recurring/run-due", headers=CRON_HEADERS)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["due"] == 1
        assert data["created"] == 1
        assert data["failed"] == 0

        donation = Donation.query.filter_by(recurring_donation_id=rec.id).first()
        assert donation is not None
        assert donation.status == "pending"
        assert donation.amount == rec.amount
        assert donation.checkout_request_id == "ws_CO_RECURRING_1"

        db.session.refresh(rec)
        assert rec.next_run_date == expected_next

    def test_second_run_same_day_does_not_double_charge(
        self, client, db, donor_user, approved_charity
    ):
        rec = _make_recurring(db, donor_user, approved_charity, days_from_today=0)

        with patch(
            "app.routes.recurring.mpesa_service.stk_push", return_value=STK_OK
        ):
            client.post("/api/recurring/run-due", headers=CRON_HEADERS)

            # Force the record to look due again, as a crashed run would.
            rec.next_run_date = date.today()
            db.session.commit()

            resp = client.post("/api/recurring/run-due", headers=CRON_HEADERS)

        data = resp.get_json()["data"]
        assert data["skipped"] == 1
        assert data["created"] == 0
        assert Donation.query.filter_by(recurring_donation_id=rec.id).count() == 1

    def test_one_failed_push_does_not_block_the_batch(
        self, client, db, donor_user, approved_charity
    ):
        first = _make_recurring(db, donor_user, approved_charity, amount=500)
        second = _make_recurring(db, donor_user, approved_charity, amount=750)

        with patch(
            "app.routes.recurring.mpesa_service.stk_push",
            side_effect=[Exception("Daraja is down"), STK_OK],
        ):
            resp = client.post("/api/recurring/run-due", headers=CRON_HEADERS)

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["due"] == 2
        assert data["created"] == 2
        assert data["failed"] == 1

        # Both records still got a donation and moved to the next month
        for rec in (first, second):
            db.session.refresh(rec)
            assert rec.next_run_date > date.today()
            assert Donation.query.filter_by(recurring_donation_id=rec.id).count() == 1

        # The second one was charged normally after the first failed
        second_donation = Donation.query.filter_by(recurring_donation_id=second.id).one()
        assert second_donation.checkout_request_id == "ws_CO_RECURRING_1"

    def test_paused_donations_are_not_charged(
        self, client, db, donor_user, approved_charity
    ):
        _make_recurring(
            db, donor_user, approved_charity, days_from_today=0, status="paused"
        )

        resp = client.post("/api/recurring/run-due", headers=CRON_HEADERS)

        assert resp.get_json()["data"]["due"] == 0
        assert Donation.query.count() == 0
