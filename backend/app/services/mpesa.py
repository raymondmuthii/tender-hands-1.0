"""Safaricom Daraja M-Pesa STK Push integration.

Environment variables consumed:
  MPESA_CONSUMER_KEY      – Daraja app consumer key
  MPESA_CONSUMER_SECRET   – Daraja app consumer secret
  MPESA_SHORTCODE         – Business shortcode (174379 for sandbox)
  MPESA_PASSKEY           – Lipa Na M-Pesa online passkey
  MPESA_CALLBACK_URL      – Public HTTPS URL for Daraja to POST results to
  MPESA_ENV               – "sandbox" | "production"  (default: sandbox)

Daraja requirements honoured here (see docs/mpesa-testing.md):
  * Timestamp is YYYYMMDDHHmmss in East Africa Time, and the exact same string
    is used to build the password – a mismatch is rejected by Safaricom.
  * Amount is a whole number of KES.
  * Phone numbers go out as 2547XXXXXXXX (no "+", no leading zero).
  * AccountReference is at most 12 characters, TransactionDesc at most 13.
"""

import base64
import logging
import re
from datetime import datetime, timedelta, timezone

import requests
from flask import current_app

logger = logging.getLogger(__name__)

_SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
_PROD_BASE = "https://api.safaricom.co.ke"

# Kenya has been UTC+3 all year round since 1960 (no daylight saving), so a
# fixed offset is exact and does not rely on the host's timezone database.
EAT = timezone(timedelta(hours=3))

# 254 followed by a Kenyan mobile prefix (Safaricom 7xx, Airtel 1xx)
_MSISDN_RE = re.compile(r"^254(7\d{8}|1\d{8})$")


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
        # Kept short: the whole request has to finish inside the hosting
        # function limit, or the browser gets a gateway error instead of a
        # readable JSON response.
        timeout=5,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _timestamp() -> str:
    """Current East Africa Time as YYYYMMDDHHmmss."""
    return datetime.now(EAT).strftime("%Y%m%d%H%M%S")


def _build_password(shortcode: str, passkey: str, timestamp: str) -> str:
    """Base64(shortcode + passkey + timestamp)."""
    raw = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(raw.encode()).decode()


def normalize_msisdn(phone: str) -> str:
    """Convert a Kenyan number to the 254XXXXXXXXX form Daraja expects.

    Accepts +254712345678, 254712345678, 0712345678, 712345678 and any of
    those with spaces or dashes. Raises ValueError for anything else so a
    rejected phone is logged instead of being sent to Safaricom.
    """
    digits = re.sub(r"\D", "", phone or "")

    if digits.startswith("254") and len(digits) == 12:
        msisdn = digits
    elif digits.startswith("0") and len(digits) == 10:
        msisdn = f"254{digits[1:]}"
    elif len(digits) == 9:
        msisdn = f"254{digits}"
    else:
        msisdn = digits

    if not _MSISDN_RE.match(msisdn):
        raise ValueError(f"Invalid Kenyan phone number: {phone!r}")
    return msisdn


def _as_int(value, default=None):
    """Coerce a Daraja field that may arrive as int, str or None."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def stk_push(phone: str, amount: int, account_reference: str, description: str) -> dict:
    """Initiate an STK Push request.

    Args:
        phone:              Donor phone in +254XXXXXXXXX format.
        amount:             Amount in KES (integer).
        account_reference:  Short label (e.g. charity slug, max 12 chars).
        description:        Human-readable description (max 13 chars).

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
        ValueError if the phone number cannot be normalised.
        KeyError if env vars are missing.
    """
    shortcode = current_app.config["MPESA_SHORTCODE"]
    passkey = current_app.config["MPESA_PASSKEY"]
    callback_url = current_app.config["MPESA_CALLBACK_URL"]

    # One timestamp, used for both the password and the request body.
    timestamp = _timestamp()
    password = _build_password(shortcode, passkey, timestamp)

    msisdn = normalize_msisdn(phone)

    token = _get_access_token()
    url = f"{_base_url()}/mpesa/stkpush/v1/processrequest"

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": msisdn,
        "PartyB": shortcode,
        "PhoneNumber": msisdn,
        "CallBackURL": callback_url,
        "AccountReference": account_reference[:12],
        "TransactionDesc": description[:13],
    }

    response = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    if response.status_code >= 400:
        # Daraja explains the rejection in the body (wrong passkey, unknown
        # shortcode, phone not allowed in sandbox, ...). Log it before raising
        # so the cause is visible in the server logs.
        logger.error(
            "Daraja rejected the STK push (%s): %s",
            response.status_code,
            response.text[:500],
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
    body = payload.get("Body") or {}
    stk_callback = body.get("stkCallback") or {}

    checkout_request_id = stk_callback.get("CheckoutRequestID") or ""
    result_code = _as_int(stk_callback.get("ResultCode"), -1)
    result_desc = stk_callback.get("ResultDesc") or ""

    mpesa_receipt = None
    amount = None
    phone = None

    # CallbackMetadata only exists for successful payments
    if result_code == 0:
        metadata = stk_callback.get("CallbackMetadata") or {}
        items = metadata.get("Item") or []
        item_map = {
            item.get("Name"): item.get("Value")
            for item in items
            if isinstance(item, dict) and item.get("Name")
        }
        mpesa_receipt = item_map.get("MpesaReceiptNumber")
        amount = _as_int(item_map.get("Amount"))

        phone_raw = item_map.get("PhoneNumber")
        if phone_raw not in (None, ""):
            try:
                phone = f"+{normalize_msisdn(str(phone_raw))}"
            except ValueError:
                phone = str(phone_raw)

    return {
        "checkout_request_id": checkout_request_id,
        "result_code": result_code,
        "result_desc": result_desc,
        "mpesa_receipt": mpesa_receipt,
        "amount": amount,
        "phone": phone,
    }
