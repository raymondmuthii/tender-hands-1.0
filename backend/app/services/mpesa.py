"""Safaricom Daraja M-Pesa STK Push integration.

Environment variables consumed:
  MPESA_CONSUMER_KEY      – Daraja app consumer key
  MPESA_CONSUMER_SECRET   – Daraja app consumer secret
  MPESA_SHORTCODE         – Business shortcode (174379 for sandbox)
  MPESA_PASSKEY           – Lipa Na M-Pesa online passkey
  MPESA_CALLBACK_URL      – Public HTTPS URL for Daraja to POST results to
  MPESA_ENV               – "sandbox" | "production"  (default: sandbox)
"""

import base64
import logging
from datetime import datetime, timezone

import requests
from flask import current_app

logger = logging.getLogger(__name__)

_SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
_PROD_BASE = "https://api.safaricom.co.ke"


def _base_url() -> str:
    env = current_app.config.get("MPESA_ENV", "sandbox")
    return _PROD_BASE if env == "production" else _SANDBOX_BASE


def _get_access_token() -> str:
    """Fetch a short-lived OAuth2 bearer token from Daraja."""
    key = current_app.config["MPESA_CONSUMER_KEY"]
    secret = current_app.config["MPESA_CONSUMER_SECRET"]
    credentials = base64.b64encode(f"{key}:{secret}".encode()).decode()

    url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(
        url,
        headers={"Authorization": f"Basic {credentials}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _build_password(shortcode: str, passkey: str, timestamp: str) -> str:
    """Base64(shortcode + passkey + timestamp)."""
    raw = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(raw.encode()).decode()


def stk_push(phone: str, amount: int, account_reference: str, description: str) -> dict:
    """Initiate an STK Push request.

    Args:
        phone:              Donor phone in +254XXXXXXXXX format.
        amount:             Amount in KES (integer).
        account_reference:  Short label (e.g. charity slug, max 12 chars).
        description:        Human-readable description (max 20 chars).

    Returns:
        Daraja response dict containing at minimum:
        {
            "MerchantRequestID": "...",
            "CheckoutRequestID": "...",
            "ResponseCode": "0",
            "ResponseDescription": "Success. Request accepted for processing",
            "CustomerMessage": "..."
        }

    Raises:
        requests.HTTPError on non-2xx responses.
        KeyError if env vars are missing.
    """
    shortcode = current_app.config["MPESA_SHORTCODE"]
    passkey = current_app.config["MPESA_PASSKEY"]
    callback_url = current_app.config["MPESA_CALLBACK_URL"]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    password = _build_password(shortcode, passkey, timestamp)

    # Daraja expects phone without the leading '+': 254XXXXXXXXX
    normalized_phone = phone.lstrip("+")

    token = _get_access_token()
    url = f"{_base_url()}/mpesa/stkpush/v1/processrequest"

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": normalized_phone,
        "PartyB": shortcode,
        "PhoneNumber": normalized_phone,
        "CallBackURL": callback_url,
        "AccountReference": account_reference[:12],
        "TransactionDesc": description[:20],
    }

    response = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("ResponseCode") != "0":
        logger.error("STK Push non-zero response: %s", data)

    return data


def parse_callback(payload: dict) -> dict:
    """Extract result fields from a Daraja STK callback payload.

    Returns a normalised dict:
    {
        "checkout_request_id": str,
        "result_code": int,          # 0 = success
        "result_desc": str,
        "mpesa_receipt": str | None, # MpesaReceiptNumber
        "amount": int | None,
        "phone": str | None,
    }
    """
    body = payload.get("Body", {})
    stk_callback = body.get("stkCallback", {})

    checkout_request_id = stk_callback.get("CheckoutRequestID", "")
    result_code = int(stk_callback.get("ResultCode", -1))
    result_desc = stk_callback.get("ResultDesc", "")

    mpesa_receipt = None
    amount = None
    phone = None

    if result_code == 0:
        items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        item_map = {item["Name"]: item.get("Value") for item in items}
        mpesa_receipt = item_map.get("MpesaReceiptNumber")
        amount = item_map.get("Amount")
        phone_raw = item_map.get("PhoneNumber")
        phone = f"+{phone_raw}" if phone_raw else None

    return {
        "checkout_request_id": checkout_request_id,
        "result_code": result_code,
        "result_desc": result_desc,
        "mpesa_receipt": mpesa_receipt,
        "amount": int(amount) if amount is not None else None,
        "phone": phone,
    }
