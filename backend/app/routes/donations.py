"""Donation routes: initiate, history, receipt, M-Pesa callback."""

import logging
from flask import Blueprint, request
from flask_jwt_extended import verify_jwt_in_request
from marshmallow import ValidationError

from app.extensions import db
from app.models.charity import Charity
from app.models.donation import Donation
from app.models.user import User
from app.schemas.donation_schema import (
    CreateDonationSchema,
    DonationSchema,
    DonationReceiptSchema,
)
from app.services import mpesa as mpesa_service
from app.utils import error_response, success_response, require_auth, require_donor, current_user_id

logger = logging.getLogger(__name__)

donations_bp = Blueprint("donations", __name__, url_prefix="/api")

_create_schema = CreateDonationSchema()
_donation_schema = DonationSchema()
_donations_schema = DonationSchema(many=True)
_receipt_schema = DonationReceiptSchema()


def _enrich(donation: Donation) -> dict:
    """Add charity_name to the serialized donation dict."""
    data = _donation_schema.dump(donation)
    data["charity_name"] = donation.charity.name if donation.charity else None
    return data


# ---------------------------------------------------------------------------
# Initiate donation
# ---------------------------------------------------------------------------

@donations_bp.post("/donations")
@require_donor
def create_donation():
    user_id = current_user_id()
    user = db.session.get(User, user_id)

    json_data = request.get_json(silent=True) or {}
    try:
        data = _create_schema.load(json_data)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    charity = Charity.query.filter_by(slug=data["charity_id"], status="approved").first()
    if not charity:
        return error_response("Charity not found or not approved.", 404)

    phone = User.normalize_phone(data["phone"])

    # Create a pending donation record first
    donation = Donation(
        user_id=user_id,
        charity_id=charity.id,
        amount=data["amount"],
        phone=phone,
        status="pending",
    )
    db.session.add(donation)
    db.session.flush()  # get donation.id before commit

    # Attempt STK push; if M-Pesa creds are not configured, record without push
    try:
        result = mpesa_service.stk_push(
            phone=phone,
            amount=data["amount"],
            account_reference=charity.slug,
            description=f"Donation to {charity.name}"[:20],
        )
        donation.checkout_request_id = result.get("CheckoutRequestID")
    except Exception as exc:
        logger.warning("STK Push failed (may be unconfigured in dev): %s", exc)
        donation.checkout_request_id = None

    db.session.commit()

    return success_response(
        {
            "donation_id": donation.id,
            "status": donation.status,
            "checkout_request_id": donation.checkout_request_id,
            "message": "STK push sent. Complete payment on your phone.",
        },
        201,
    )


# ---------------------------------------------------------------------------
# Donor history
# ---------------------------------------------------------------------------

@donations_bp.get("/donations/me")
@require_donor
def my_donations():
    user_id = current_user_id()
    donations = (
        Donation.query.filter_by(user_id=user_id)
        .order_by(Donation.created_at.desc())
        .all()
    )
    return success_response([_enrich(d) for d in donations])


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------

@donations_bp.get("/donations/<int:donation_id>/receipt")
@require_auth
def get_receipt(donation_id: int):
    user_id = current_user_id()
    user = db.session.get(User, user_id)

    donation = db.session.get(Donation, donation_id)
    if not donation:
        return error_response("Donation not found.", 404)

    # Donors can only see their own receipts; admins see all
    if user.role != "admin" and donation.user_id != user_id:
        return error_response("Access denied.", 403)

    if donation.status != "completed":
        return error_response("Receipt not available for non-completed donations.", 400)

    data = _receipt_schema.dump(donation)
    data["charity_name"] = donation.charity.name if donation.charity else None
    return success_response(data)


# ---------------------------------------------------------------------------
# M-Pesa callback (no auth – called by Safaricom)
# ---------------------------------------------------------------------------

@donations_bp.post("/mpesa/callback")
def mpesa_callback():
    payload = request.get_json(silent=True) or {}
    try:
        result = mpesa_service.parse_callback(payload)
    except Exception as exc:
        logger.error("Failed to parse M-Pesa callback: %s", exc)
        return {"ResultCode": 1, "ResultDesc": "Internal error"}, 500

    checkout_id = result.get("checkout_request_id")
    if not checkout_id:
        return {"ResultCode": 0, "ResultDesc": "OK"}, 200

    donation = Donation.query.filter_by(checkout_request_id=checkout_id).first()
    if not donation:
        logger.warning("Callback for unknown checkout_request_id: %s", checkout_id)
        return {"ResultCode": 0, "ResultDesc": "OK"}, 200

    if result["result_code"] == 0:
        donation.status = "completed"
        donation.mpesa_receipt = result.get("mpesa_receipt")
    else:
        donation.status = "failed"
        logger.info(
            "Donation %s failed: %s", donation.id, result.get("result_desc")
        )

    db.session.commit()
    return {"ResultCode": 0, "ResultDesc": "Accepted"}, 200
