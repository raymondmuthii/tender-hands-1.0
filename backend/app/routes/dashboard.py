"""Donor dashboard summary route."""

from flask import Blueprint
# flask_jwt_extended used via current_user_id() helper
from sqlalchemy import func

from app.extensions import db
from app.models.donation import Donation, RecurringDonation
from app.models.charity import Charity
from app.schemas.donation_schema import DonationSchema
from app.utils import success_response, require_donor, current_user_id

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

_donation_schema = DonationSchema()


@dashboard_bp.get("/summary")
@require_donor
def summary():
    user_id = current_user_id()

    # Total donated (completed donations only)
    total_donated = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.user_id == user_id, Donation.status == "completed")
        .scalar()
    )

    # Number of distinct charities supported
    charities_supported = (
        db.session.query(func.count(func.distinct(Donation.charity_id)))
        .filter(Donation.user_id == user_id, Donation.status == "completed")
        .scalar()
    )

    # Monthly giving: sum of active recurring donation amounts
    monthly_giving = (
        db.session.query(func.coalesce(func.sum(RecurringDonation.amount), 0))
        .filter(
            RecurringDonation.user_id == user_id,
            RecurringDonation.status == "active",
        )
        .scalar()
    )

    # 5 most recent completed donations with charity name
    recent = (
        Donation.query.filter_by(user_id=user_id, status="completed")
        .order_by(Donation.created_at.desc())
        .limit(5)
        .all()
    )
    recent_data = []
    for d in recent:
        row = _donation_schema.dump(d)
        row["charity_name"] = d.charity.name if d.charity else None
        recent_data.append(row)

    return success_response(
        {
            "total_donated": int(total_donated),
            "charities_supported": int(charities_supported),
            "monthly_giving": int(monthly_giving),
            "recent_donations": recent_data,
        }
    )
