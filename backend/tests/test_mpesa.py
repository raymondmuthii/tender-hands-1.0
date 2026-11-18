"""Tests for the Daraja STK Push helper and callback parsing."""

import base64
import re
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.services import mpesa


class TestPasswordAndTimestamp:
    def test_password_is_base64_of_shortcode_passkey_timestamp(self):
        expected = base64.b64encode(b"174379passkey20261118120000").decode()
        assert mpesa._build_password("174379", "passkey", "20261118120000") == expected

    def test_timestamp_is_east_africa_time(self):
        """Daraja validates the timestamp against Nairobi time, not UTC."""
        stamp = mpesa._timestamp()
        assert re.fullmatch(r"\d{14}", stamp)

        parsed = datetime.strptime(stamp, "%Y%m%d%H%M%S")
        eat_now = datetime.now(mpesa.EAT).replace(tzinfo=None)
        utc_now = datetime.now(timezone.utc).replace(tzinfo=None)

        # The wall clock in the timestamp is EAT...
        assert abs((parsed - eat_now).total_seconds()) < 60
        # ...and EAT is three hours ahead of UTC.
        assert round((eat_now - utc_now).total_seconds()) == 3 * 3600


class TestNormalizeMsisdn:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("+254712345678", "254712345678"),
            ("254712345678", "254712345678"),
            ("0712345678", "254712345678"),
            ("712345678", "254712345678"),
            ("+254 712 345 678", "254712345678"),
            ("0722-000-099", "254722000099"),
        ],
    )
    def test_accepts_common_formats(self, raw, expected):
        assert mpesa.normalize_msisdn(raw) == expected

    @pytest.mark.parametrize("raw", ["0800123456", "abc", "", "+447700900123"])
    def test_rejects_invalid_numbers(self, raw):
        with pytest.raises(ValueError):
            mpesa.normalize_msisdn(raw)


class TestStkPushPayload:
    def test_payload_matches_daraja_requirements(self, app, monkeypatch):
        monkeypatch.setitem(app.config, "MPESA_ENV", "sandbox")
        monkeypatch.setitem(app.config, "MPESA_SHORTCODE", "174379")
        monkeypatch.setitem(app.config, "MPESA_PASSKEY", "test-passkey")
        monkeypatch.setitem(
            app.config, "MPESA_CALLBACK_URL", "https://example.com/api/mpesa/callback"
        )

        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"ResponseCode": "0", "CheckoutRequestID": "ws_CO_TEST"}

        def fake_post(url, json=None, headers=None, timeout=None):
            captured["url"] = url
            captured["payload"] = json
            captured["headers"] = headers
            return FakeResponse()

        with app.app_context():
            with patch.object(mpesa, "_get_access_token", return_value="token"), patch.object(
                mpesa.requests, "post", side_effect=fake_post
            ):
                result = mpesa.stk_push(
                    phone="0722 000 099",
                    amount=1500,
                    account_reference="amani-learning",
                    description="Donation to Amani Learning Trust",
                )

        payload = captured["payload"]
        assert result["CheckoutRequestID"] == "ws_CO_TEST"
        assert captured["url"].endswith("/mpesa/stkpush/v1/processrequest")
        assert captured["headers"]["Authorization"] == "Bearer token"

        assert payload["PhoneNumber"] == "254722000099"
        assert payload["PartyA"] == "254722000099"
        assert payload["PartyB"] == "174379"
        assert payload["TransactionType"] == "CustomerPayBillOnline"

        # Amount must be a whole number, not a string or float
        assert payload["Amount"] == 1500
        assert isinstance(payload["Amount"], int)

        # Password must be built from the exact timestamp that is sent
        assert payload["Password"] == mpesa._build_password(
            "174379", "test-passkey", payload["Timestamp"]
        )
        assert len(payload["Timestamp"]) == 14
        assert len(payload["AccountReference"]) <= 12
        assert len(payload["TransactionDesc"]) <= 13
        assert payload["CallBackURL"] == "https://example.com/api/mpesa/callback"

    def test_invalid_phone_raises_before_calling_daraja(self, app, monkeypatch):
        monkeypatch.setitem(app.config, "MPESA_SHORTCODE", "174379")
        monkeypatch.setitem(app.config, "MPESA_PASSKEY", "test-passkey")

        with app.app_context():
            with patch.object(mpesa, "_get_access_token") as token:
                with pytest.raises(ValueError):
                    mpesa.stk_push("nonsense", 10, "amani", "Test")
                token.assert_not_called()


SUCCESS_CALLBACK = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "29115-34620561-1",
            "CheckoutRequestID": "ws_CO_191220191020363925",
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

FAILURE_CALLBACK = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "29115-34620561-2",
            "CheckoutRequestID": "ws_CO_FAIL",
            "ResultCode": 1032,
            "ResultDesc": "Request cancelled by user",
        }
    }
}


class TestParseCallback:
    def test_success_payload(self):
        result = mpesa.parse_callback(SUCCESS_CALLBACK)
        assert result == {
            "checkout_request_id": "ws_CO_191220191020363925",
            "result_code": 0,
            "result_desc": "The service request is processed successfully.",
            "mpesa_receipt": "QHX999TEST",
            "amount": 1000,
            "phone": "+254722000099",
        }

    def test_failure_payload_has_no_payment_details(self):
        result = mpesa.parse_callback(FAILURE_CALLBACK)
        assert result["result_code"] == 1032
        assert result["result_desc"] == "Request cancelled by user"
        assert result["mpesa_receipt"] is None
        assert result["amount"] is None
        assert result["phone"] is None

    def test_string_result_code_and_amount_are_coerced(self):
        payload = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "ws_CO_STRING",
                    "ResultCode": "0",
                    "ResultDesc": "ok",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": "1500"},
                            {"Name": "MpesaReceiptNumber", "Value": "QHX1"},
                            {"Name": "PhoneNumber", "Value": "254712345678"},
                        ]
                    },
                }
            }
        }
        result = mpesa.parse_callback(payload)
        assert result["result_code"] == 0
        assert result["amount"] == 1500
        assert result["phone"] == "+254712345678"

    def test_missing_result_code_does_not_raise(self):
        result = mpesa.parse_callback(
            {"Body": {"stkCallback": {"CheckoutRequestID": "ws_CO_X"}}}
        )
        assert result["result_code"] == -1
        assert result["mpesa_receipt"] is None

    def test_empty_payload_does_not_raise(self):
        result = mpesa.parse_callback({})
        assert result["checkout_request_id"] == ""
        assert result["result_code"] == -1
