"""Charity routes: public listing, detail, application, management."""

from flask import Blueprint, request
from flask_jwt_extended import verify_jwt_in_request
from marshmallow import ValidationError

from app.extensions import db
from app.models.charity import Charity, ImpactStory, Beneficiary, InventoryItem
from app.models.user import User
from app.schemas.charity_schema import (
    CharitySchema,
    CharityDetailSchema,
    CreateCharitySchema,
    UpdateCharitySchema,
    ImpactStorySchema,
    BeneficiarySchema,
    InventoryItemSchema,
)
from app.utils import error_response, success_response, require_charity, require_auth, current_user_id

charities_bp = Blueprint("charities", __name__, url_prefix="/api/charities")

_charity_schema = CharitySchema()
_charities_schema = CharitySchema(many=True)
_detail_schema = CharityDetailSchema()
_create_schema = CreateCharitySchema()
_update_schema = UpdateCharitySchema()
_story_schema = ImpactStorySchema()
_stories_schema = ImpactStorySchema(many=True)
_beneficiary_schema = BeneficiarySchema()
_beneficiaries_schema = BeneficiarySchema(many=True)
_inventory_schema = InventoryItemSchema()
_inventories_schema = InventoryItemSchema(many=True)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@charities_bp.get("")
def list_charities():
    query = Charity.query.filter_by(status="approved")

    category = request.args.get("category")
    if category:
        query = query.filter(Charity.category == category)

    featured = request.args.get("featured")
    if featured and featured.lower() in ("true", "1"):
        query = query.filter(Charity.is_featured.is_(True))

    search = request.args.get("search", "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Charity.name.ilike(like),
                Charity.location.ilike(like),
                Charity.description.ilike(like),
            )
        )

    # Pagination
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(50, request.args.get("per_page", 12, type=int))
    pagination = query.order_by(Charity.is_featured.desc(), Charity.id).paginate(
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


@charities_bp.get("/<slug>")
def get_charity(slug: str):
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity:
        return error_response("Charity not found.", 404)

    # Non-approved charities are visible only to their owner or an admin
    if charity.status != "approved":
        try:
            verify_jwt_in_request()
            user_id = current_user_id()
            user = db.session.get(User, user_id)
            if user is None or (user.role != "admin" and charity.owner_id != user_id):
                return error_response("Charity not found.", 404)
        except Exception:
            return error_response("Charity not found.", 404)

    return success_response(_detail_schema.dump(charity))


# ---------------------------------------------------------------------------
# Charity application (authenticated)
# ---------------------------------------------------------------------------

@charities_bp.post("")
@require_charity
def create_charity():
    user_id = current_user_id()
    json_data = request.get_json(silent=True) or {}
    try:
        data = _create_schema.load(json_data)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    if Charity.query.filter_by(slug=data["slug"]).first():
        return error_response("A charity with that slug already exists.", 409)

    charity = Charity(
        slug=data["slug"],
        name=data["name"],
        category=data["category"],
        location=data["location"],
        description=data["description"],
        image_url=data.get("image_url"),
        goal_amount=data["goal_amount"],
        owner_id=user_id,
        status="pending",
    )
    db.session.add(charity)
    db.session.commit()
    return success_response(_detail_schema.dump(charity), 201)


@charities_bp.patch("/<slug>")
@require_auth
def update_charity(slug: str):
    user_id = current_user_id()
    user = db.session.get(User, user_id)

    charity = Charity.query.filter_by(slug=slug).first()
    if not charity:
        return error_response("Charity not found.", 404)

    # Only the owner or an admin may update
    if user.role != "admin" and charity.owner_id != user_id:
        return error_response("Access denied.", 403)

    json_data = request.get_json(silent=True) or {}
    try:
        data = _update_schema.load(json_data)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    for field, value in data.items():
        setattr(charity, field, value)

    db.session.commit()
    return success_response(_detail_schema.dump(charity))


# ---------------------------------------------------------------------------
# Impact Stories (owner-managed, publicly readable)
# ---------------------------------------------------------------------------

@charities_bp.get("/<slug>/stories")
def list_stories(slug: str):
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity:
        return error_response("Charity not found.", 404)
    stories = charity.impact_stories.filter_by(published=True).all()
    return success_response(_stories_schema.dump(stories))


@charities_bp.post("/<slug>/stories")
@require_charity
def create_story(slug: str):
    user_id = current_user_id()
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity:
        return error_response("Charity not found.", 404)
    if charity.owner_id != user_id:
        return error_response("Access denied.", 403)

    json_data = request.get_json(silent=True) or {}
    try:
        data = _story_schema.load(json_data)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    story = ImpactStory(charity_id=charity.id, **data)
    db.session.add(story)
    db.session.commit()
    return success_response(_story_schema.dump(story), 201)


@charities_bp.patch("/<slug>/stories/<int:story_id>")
@require_charity
def update_story(slug: str, story_id: int):
    user_id = current_user_id()
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity or charity.owner_id != user_id:
        return error_response("Access denied.", 403)

    story = db.session.get(ImpactStory, story_id)
    if not story or story.charity_id != charity.id:
        return error_response("Story not found.", 404)

    json_data = request.get_json(silent=True) or {}
    try:
        data = _story_schema.load(json_data, partial=True)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    for field, value in data.items():
        setattr(story, field, value)

    db.session.commit()
    return success_response(_story_schema.dump(story))


@charities_bp.delete("/<slug>/stories/<int:story_id>")
@require_charity
def delete_story(slug: str, story_id: int):
    user_id = current_user_id()
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity or charity.owner_id != user_id:
        return error_response("Access denied.", 403)

    story = db.session.get(ImpactStory, story_id)
    if not story or story.charity_id != charity.id:
        return error_response("Story not found.", 404)

    db.session.delete(story)
    db.session.commit()
    return success_response({"deleted": story_id})


# ---------------------------------------------------------------------------
# Beneficiaries
# ---------------------------------------------------------------------------

@charities_bp.get("/<slug>/beneficiaries")
@require_charity
def list_beneficiaries(slug: str):
    user_id = current_user_id()
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity or charity.owner_id != user_id:
        return error_response("Access denied.", 403)
    return success_response(_beneficiaries_schema.dump(charity.beneficiaries.all()))


@charities_bp.post("/<slug>/beneficiaries")
@require_charity
def create_beneficiary(slug: str):
    user_id = current_user_id()
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity or charity.owner_id != user_id:
        return error_response("Access denied.", 403)

    json_data = request.get_json(silent=True) or {}
    try:
        data = _beneficiary_schema.load(json_data)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    beneficiary = Beneficiary(charity_id=charity.id, **data)
    db.session.add(beneficiary)
    db.session.commit()
    return success_response(_beneficiary_schema.dump(beneficiary), 201)


@charities_bp.patch("/<slug>/beneficiaries/<int:ben_id>")
@require_charity
def update_beneficiary(slug: str, ben_id: int):
    user_id = current_user_id()
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity or charity.owner_id != user_id:
        return error_response("Access denied.", 403)

    ben = db.session.get(Beneficiary, ben_id)
    if not ben or ben.charity_id != charity.id:
        return error_response("Beneficiary not found.", 404)

    json_data = request.get_json(silent=True) or {}
    try:
        data = _beneficiary_schema.load(json_data, partial=True)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    for field, value in data.items():
        setattr(ben, field, value)

    db.session.commit()
    return success_response(_beneficiary_schema.dump(ben))


@charities_bp.delete("/<slug>/beneficiaries/<int:ben_id>")
@require_charity
def delete_beneficiary(slug: str, ben_id: int):
    user_id = current_user_id()
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity or charity.owner_id != user_id:
        return error_response("Access denied.", 403)

    ben = db.session.get(Beneficiary, ben_id)
    if not ben or ben.charity_id != charity.id:
        return error_response("Beneficiary not found.", 404)

    db.session.delete(ben)
    db.session.commit()
    return success_response({"deleted": ben_id})


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

@charities_bp.get("/<slug>/inventory")
@require_charity
def list_inventory(slug: str):
    user_id = current_user_id()
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity or charity.owner_id != user_id:
        return error_response("Access denied.", 403)
    return success_response(_inventories_schema.dump(charity.inventory_items.all()))


@charities_bp.post("/<slug>/inventory")
@require_charity
def create_inventory_item(slug: str):
    user_id = current_user_id()
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity or charity.owner_id != user_id:
        return error_response("Access denied.", 403)

    json_data = request.get_json(silent=True) or {}
    try:
        data = _inventory_schema.load(json_data)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    item = InventoryItem(charity_id=charity.id, **data)
    db.session.add(item)
    db.session.commit()
    return success_response(_inventory_schema.dump(item), 201)


@charities_bp.patch("/<slug>/inventory/<int:item_id>")
@require_charity
def update_inventory_item(slug: str, item_id: int):
    user_id = current_user_id()
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity or charity.owner_id != user_id:
        return error_response("Access denied.", 403)

    item = db.session.get(InventoryItem, item_id)
    if not item or item.charity_id != charity.id:
        return error_response("Item not found.", 404)

    json_data = request.get_json(silent=True) or {}
    try:
        data = _inventory_schema.load(json_data, partial=True)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    for field, value in data.items():
        setattr(item, field, value)

    db.session.commit()
    return success_response(_inventory_schema.dump(item))


@charities_bp.delete("/<slug>/inventory/<int:item_id>")
@require_charity
def delete_inventory_item(slug: str, item_id: int):
    user_id = current_user_id()
    charity = Charity.query.filter_by(slug=slug).first()
    if not charity or charity.owner_id != user_id:
        return error_response("Access denied.", 403)

    item = db.session.get(InventoryItem, item_id)
    if not item or item.charity_id != charity.id:
        return error_response("Item not found.", 404)

    db.session.delete(item)
    db.session.commit()
    return success_response({"deleted": item_id})
