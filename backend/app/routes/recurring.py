"""Recurring donation routes."""

from flask import Blueprint, request
# flask_jwt_extended used via current_user_id() helper
from marshmallow import ValidationError

from app.extensions import db
from app.models.charity import Charity
from app.models.donation import RecurringDonation
from app.schemas.donation_schema import (
    CreateRecurringSchema,
    UpdateRecurringSchema,
    RecurringDonationSchema,
)
from app.utils import error_response, success_response, require_donor, current_user_id

recurring_bp = Blueprint("recurring", __name__, url_prefix="/api/recurring")

_create_schema = CreateRecurringSchema()
_update_schema = UpdateRecurringSchema()
_schema = RecurringDonationSchema()
_many_schema = RecurringDonationSchema(many=True)


def _enrich(rec: RecurringDonation) -> dict:
    data = _schema.dump(rec)
    data["charity_name"] = rec.charity.name if rec.charity else None
    return data


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
