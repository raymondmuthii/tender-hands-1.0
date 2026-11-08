"""Admin-only routes: charity approval, platform stats."""

from flask import Blueprint, request
from sqlalchemy import func

from app.extensions import db
from app.models.charity import Charity
from app.models.donation import Donation
from app.models.user import User
from app.schemas.charity_schema import CharityDetailSchema
from app.utils import error_response, success_response, require_admin

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

_detail_schema = CharityDetailSchema()
_charities_schema = CharityDetailSchema(many=True)


@admin_bp.get("/charities")
@require_admin
def list_charities():
    status = request.args.get("status")
    query = Charity.query
    if status:
        query = query.filter(Charity.status == status)
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, request.args.get("per_page", 20, type=int))
    pagination = query.order_by(Charity.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return success_response(
        _charities_schema.dump(pagination.items),
        meta={
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        },
    )


@admin_bp.post("/charities/<slug>/approve")
@require_admin
def approve_charity(slug: str):
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity:
        return error_response("Charity not found.", 404)
    charity.status = "approved"
    db.session.commit()
    return success_response(_detail_schema.dump(charity))


@admin_bp.post("/charities/<slug>/reject")
@require_admin
def reject_charity(slug: str):
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity:
        return error_response("Charity not found.", 404)
    charity.status = "rejected"
    db.session.commit()
    return success_response(_detail_schema.dump(charity))


@admin_bp.post("/charities/<slug>/feature")
@require_admin
def toggle_feature(slug: str):
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity:
        return error_response("Charity not found.", 404)
    charity.is_featured = not charity.is_featured
    db.session.commit()
    return success_response(
        {"slug": charity.slug, "is_featured": charity.is_featured}
    )


@admin_bp.get("/stats")
@require_admin
def stats():
    total_users = User.query.count()
    total_charities = Charity.query.count()
    pending_charities = Charity.query.filter_by(status="pending").count()
    approved_charities = Charity.query.filter_by(status="approved").count()
    total_donations = Donation.query.filter_by(status="completed").count()
    total_raised = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.status == "completed")
        .scalar()
    )

    return success_response(
        {
            "total_users": total_users,
            "total_charities": total_charities,
            "pending_charities": pending_charities,
            "approved_charities": approved_charities,
            "total_donations": total_donations,
            "total_raised_kes": int(total_raised),
        }
    )
