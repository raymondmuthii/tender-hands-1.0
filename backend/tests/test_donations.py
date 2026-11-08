"""Tests for the donation lifecycle including the M-Pesa callback."""

import pytest
from unittest.mock import patch
from app.models.donation import Donation


class TestCreateDonation:
    def _donate(self, client, token, charity_slug="test-charity", amount=500, phone="+254722000099"):
        return client.post(
            "/api/donations",
            json={"charity_id": charity_slug, "amount": amount, "phone": phone},
            headers={"Authorization": f"Bearer {token}"},
        )

    def test_create_donation_stk_push_attempted(
        self, client, approved_charity, donor_tokens
    ):
        access, _ = donor_tokens
        fake_response = {
            "MerchantRequestID": "abc-123",
            "CheckoutRequestID": "ws_CO_TEST123",
            "ResponseCode": "0",
            "ResponseDescription": "Success",
            "CustomerMessage": "Success",
        }
        with patch("app.routes.donations.mpesa_service.stk_push", return_value=fake_response):
            resp = self._donate(client, access)

        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["status"] == "pending"
        assert data["checkout_request_id"] == "ws_CO_TEST123"

    def test_create_donation_stk_push_failure_still_creates_record(
        self, client, approved_charity, donor_tokens
    ):
        access, _ = donor_tokens
        with patch(
            "app.routes.donations.mpesa_service.stk_push",
            side_effect=Exception("Network error"),
        ):
            resp = self._donate(client, access)

        assert resp.status_code == 201
        assert resp.get_json()["data"]["status"] == "pending"

    def test_create_donation_unapproved_charity(
        self, client, db, charity_user, donor_tokens
    ):
        from app.models.charity import Charity
        pending = Charity(
            slug="pending-for-donation",
            name="Pending",
            category="Education",
            location="Nairobi",
            description="Pending charity cannot receive donations.",
            goal_amount=10_000,
            owner_id=charity_user.id,
            status="pending",
        )
        db.session.add(pending)
        db.session.commit()

        access, _ = donor_tokens
        resp = self._donate(client, access, charity_slug="pending-for-donation")
        assert resp.status_code == 404

    def test_create_donation_requires_auth(self, client, approved_charity):
        resp = client.post(
            "/api/donations",
            json={"charity_id": "test-charity", "amount": 500, "phone": "+254722000099"},
        )
        assert resp.status_code == 401

    def test_create_donation_min_amount(self, client, approved_charity, donor_tokens):
        access, _ = donor_tokens
        with patch("app.routes.donations.mpesa_service.stk_push", return_value={}):
            resp = self._donate(client, access, amount=5)  # below KES 10 minimum
        assert resp.status_code == 422


class TestDonationHistory:
    def test_my_donations(self, client, db, approved_charity, donor_user, donor_tokens):
        # Insert a completed donation directly
        d = Donation(
            user_id=donor_user.id,
            charity_id=approved_charity.id,
            amount=1_000,
            phone="+254722000099",
            mpesa_receipt="QHX001TEST",
            status="completed",
        )
        db.session.add(d)
        db.session.commit()

        access, _ = donor_tokens
        resp = client.get(
            "/api/donations/me",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        donations = resp.get_json()["data"]
        assert len(donations) >= 1
        assert donations[0]["charity_name"] == "Test Charity"

    def test_my_donations_requires_auth(self, client, db):
        resp = client.get("/api/donations/me")
        assert resp.status_code == 401


class TestMpesaCallback:
    def _callback_payload(self, checkout_id: str, success: bool = True) -> dict:
        if success:
            return {
                "Body": {
                    "stkCallback": {
                        "MerchantRequestID": "xyz",
                        "CheckoutRequestID": checkout_id,
                        "ResultCode": 0,
                        "ResultDesc": "The service request is processed successfully.",
                        "CallbackMetadata": {
                            "Item": [
                                {"Name": "Amount", "Value": 1000},
                                {"Name": "MpesaReceiptNumber", "Value": "QHX999TEST"},
                                {"Name": "TransactionDate", "Value": 20261108123456},
                                {"Name": "PhoneNumber", "Value": 254722000099},
                            ]
                        },
                    }
                }
            }
        return {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "xyz",
                    "CheckoutRequestID": checkout_id,
                    "ResultCode": 1032,
                    "ResultDesc": "Request cancelled by user.",
                }
            }
        }

    def test_callback_marks_donation_completed(
        self, client, db, approved_charity, donor_user
    ):
        donation = Donation(
            user_id=donor_user.id,
            charity_id=approved_charity.id,
            amount=1_000,
            phone="+254722000099",
            checkout_request_id="ws_CO_CALLBACK_TEST",
            status="pending",
        )
        db.session.add(donation)
        db.session.commit()

        resp = client.post(
            "/api/mpesa/callback",
            json=self._callback_payload("ws_CO_CALLBACK_TEST", success=True),
        )
        assert resp.status_code == 200

        db.session.refresh(donation)
        assert donation.status == "completed"
        assert donation.mpesa_receipt == "QHX999TEST"

    def test_callback_marks_donation_failed(
        self, client, db, approved_charity, donor_user
    ):
        donation = Donation(
            user_id=donor_user.id,
            charity_id=approved_charity.id,
            amount=500,
            phone="+254722000099",
            checkout_request_id="ws_CO_FAIL_TEST",
            status="pending",
        )
        db.session.add(donation)
        db.session.commit()

        resp = client.post(
            "/api/mpesa/callback",
            json=self._callback_payload("ws_CO_FAIL_TEST", success=False),
        )
        assert resp.status_code == 200

        db.session.refresh(donation)
        assert donation.status == "failed"

    def test_callback_unknown_checkout_id_ignored(self, client, db):
        resp = client.post(
            "/api/mpesa/callback",
            json=self._callback_payload("UNKNOWN_CHECKOUT_ID"),
        )
        assert resp.status_code == 200


class TestReceipt:
    def test_receipt_for_completed_donation(
        self, client, db, approved_charity, donor_user, donor_tokens
    ):
        d = Donation(
            user_id=donor_user.id,
            charity_id=approved_charity.id,
            amount=2_000,
            phone="+254722000099",
            mpesa_receipt="QHX002TEST",
            status="completed",
        )
        db.session.add(d)
        db.session.commit()

        access, _ = donor_tokens
        resp = client.get(
            f"/api/donations/{d.id}/receipt",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["mpesa_receipt"] == "QHX002TEST"

    def test_receipt_for_pending_donation_returns_400(
        self, client, db, approved_charity, donor_user, donor_tokens
    ):
        d = Donation(
            user_id=donor_user.id,
            charity_id=approved_charity.id,
            amount=500,
            phone="+254722000099",
            status="pending",
        )
        db.session.add(d)
        db.session.commit()

        access, _ = donor_tokens
        resp = client.get(
            f"/api/donations/{d.id}/receipt",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 400
