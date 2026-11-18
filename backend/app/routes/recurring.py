"""Recurring donation routes."""

import calendar
import hmac
import logging
from datetime import date

from flask import Blueprint, current_app, request
# flask_jwt_extended used via current_user_id() helper
from marshmallow import ValidationError
from sqlalchemy import func

from app.extensions import db
from app.models.charity import Charity
from app.models.donation import Donation, RecurringDonation
from app.schemas.donation_schema import (
    CreateRecurringSchema,
    UpdateRecurringSchema,
    RecurringDonationSchema,
)
from app.services import mpesa as mpesa_service
from app.utils import error_response, success_response, require_donor, current_user_id

logger = logging.getLogger(__name__)

recurring_bp = Blueprint("recurring", __name__, url_prefix="/api/recurring")

_create_schema = CreateRecurringSchema()
_update_schema = UpdateRecurringSchema()
_schema = RecurringDonationSchema()
_many_schema = RecurringDonationSchema(many=True)


def _enrich(rec: RecurringDonation) -> dict:
    data = _schema.dump(rec)
    data["charity_name"] = rec.charity.name if rec.charity else None
    return data


def _advance_next_run(current: date) -> date:
    """Move a monthly schedule one calendar month forward.

    Days that do not exist in the target month are clamped (31 Jan -> 28 Feb).
    """
    year = current.year + (1 if current.month == 12 else 0)
    month = 1 if current.month == 12 else current.month + 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@recurring_bp.get("")
@require_donor
def list_recurring():
    user_id = current_user_id()
    recs = (
        RecurringDonation.query.filter_by(user_id=user_id)
        .order_by(RecurringDonation.id.desc())
        .all()
    )
    return success_response([_enrich(r) for r in recs])


@recurring_bp.post("")
@require_donor
def create_recurring():
    user_id = current_user_id()
    json_data = request.get_json(silent=True) or {}
    try:
        data = _create_schema.load(json_data)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    charity = Charity.query.filter_by(slug=data["charity_id"], status="approved").first()
    if not charity:
        return error_response("Charity not found or not approved.", 404)

    rec = RecurringDonation(
        user_id=user_id,
        charity_id=charity.id,
        amount=data["amount"],
        frequency=data.get("frequency", "monthly"),
        next_run_date=data["next_run_date"],
        status="active",
    )
    db.session.add(rec)
    db.session.commit()
    return success_response(_enrich(rec), 201)


@recurring_bp.patch("/<int:rec_id>")
@require_donor
def update_recurring(rec_id: int):
    user_id = current_user_id()
    rec = db.session.get(RecurringDonation, rec_id)
    if not rec or rec.user_id != user_id:
        return error_response("Recurring donation not found.", 404)

    json_data = request.get_json(silent=True) or {}
    try:
        data = _update_schema.load(json_data)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    for field, value in data.items():
        setattr(rec, field, value)

    db.session.commit()
    return success_response(_enrich(rec))


@recurring_bp.delete("/<int:rec_id>")
@require_donor
def delete_recurring(rec_id: int):
    user_id = current_user_id()
    rec = db.session.get(RecurringDonation, rec_id)
    if not rec or rec.user_id != user_id:
        return error_response("Recurring donation not found.", 404)

    rec.status = "cancelled"
    db.session.commit()
    return success_response({"cancelled": rec_id})


# ---------------------------------------------------------------------------
# Scheduled execution (Vercel has no background worker, so a cron job calls this)
# ---------------------------------------------------------------------------

@recurring_bp.post("/run-due")
def run_due():
    """Charge every active recurring donation whose next_run_date has arrived.

    Protected by the CRON_SECRET shared secret instead of a JWT: the caller is
    an external scheduler, not a user. Safe to call more than once a day.
    """
    secret = current_app.config.get("CRON_SECRET") or ""
    provided = request.headers.get("X-Cron-Secret", "")
    if not secret or not provided or not hmac.compare_digest(provided, secret):
        return error_response("Unauthorized.", 403)

    today = date.today()
    due = (
        RecurringDonation.query.filter(
            RecurringDonation.status == "active",
            RecurringDonation.next_run_date <= today,
        )
        .order_by(RecurringDonation.id)
        .all()
    )

    created_ids: list[int] = []
    skipped: list[int] = []
    failed: list[int] = []

    for rec in due:
        try:
            # Idempotency: never charge the same recurring donation twice a day,
            # even if a previous run created the donation but failed to advance
            # the schedule.
            already_charged = Donation.query.filter(
                Donation.recurring_donation_id == rec.id,
                func.date(Donation.created_at) == today,
            ).first()
            if already_charged:
                skipped.append(rec.id)
                continue

            donation = Donation(
                user_id=rec.user_id,
                charity_id=rec.charity_id,
                amount=rec.amount,
                phone=rec.user.phone if rec.user and rec.user.phone else "",
                status="pending",
                recurring_donation_id=rec.id,
            )
            db.session.add(donation)
            db.session.flush()

            try:
                result = mpesa_service.stk_push(
                    phone=donation.phone,
                    amount=rec.amount,
                    account_reference=rec.charity.slug,
                    description=f"Recurring gift to {rec.charity.name}"[:20],
                )
                donation.checkout_request_id = result.get("CheckoutRequestID")
            except Exception as exc:
                # One failed STK push must not stop the rest of the batch
                logger.warning(
                    "STK push failed for recurring donation %s: %s", rec.id, exc
                )
                failed.append(rec.id)

            rec.next_run_date = _advance_next_run(rec.next_run_date)
            db.session.commit()
            created_ids.append(donation.id)
        except Exception as exc:
            db.session.rollback()
            logger.error("Recurring donation %s could not be processed: %s", rec.id, exc)
            failed.append(rec.id)

    logger.info(
        "Recurring run for %s: %s due, %s created, %s skipped, %s failed",
        today, len(due), len(created_ids), len(skipped), len(failed),
    )

    return success_response(
        {
            "date": today.isoformat(),
            "due": len(due),
            "created": len(created_ids),
            "skipped": len(skipped),
            "failed": len(failed),
            "donation_ids": created_ids,
        }
    )
