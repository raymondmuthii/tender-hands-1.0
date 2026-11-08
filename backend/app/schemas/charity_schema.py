"""Marshmallow schemas for Charity and sub-models."""

from marshmallow import Schema, fields, validate


VALID_CATEGORIES = ["Education", "Clean water", "Healthcare", "Livelihoods"]


class CharitySchema(Schema):
    """Public-facing charity representation matching the frontend contract."""

    # Frontend expects `id` to be the slug (string identifier)
    id = fields.Str(attribute="slug", dump_only=True)
    name = fields.Str(dump_only=True)
    category = fields.Str(dump_only=True)
    location = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True)
    image = fields.Str(attribute="image_url", dump_only=True)
    # Frontend uses `amount` and `goal`
    amount = fields.Int(attribute="amount_raised", dump_only=True)
    goal = fields.Int(attribute="goal_amount", dump_only=True)
    status = fields.Str(dump_only=True)
    is_featured = fields.Bool(dump_only=True)
    slug = fields.Str(dump_only=True)


class CharityDetailSchema(CharitySchema):
    """Full detail schema, adds owner info."""
    owner_id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class CreateCharitySchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=3, max=150))
    slug = fields.Str(required=True, validate=validate.Length(min=2, max=80))
    category = fields.Str(
        required=True, validate=validate.OneOf(VALID_CATEGORIES)
    )
    location = fields.Str(required=True, validate=validate.Length(min=2, max=150))
    description = fields.Str(required=True, validate=validate.Length(min=10))
    image_url = fields.Url(required=False, load_default=None)
    goal_amount = fields.Int(required=True, validate=validate.Range(min=1))


class UpdateCharitySchema(Schema):
    name = fields.Str(validate=validate.Length(min=3, max=150))
    category = fields.Str(validate=validate.OneOf(VALID_CATEGORIES))
    location = fields.Str(validate=validate.Length(min=2, max=150))
    description = fields.Str(validate=validate.Length(min=10))
    image_url = fields.Url(required=False)
    goal_amount = fields.Int(validate=validate.Range(min=1))


# ---- Sub-model schemas ----

class ImpactStorySchema(Schema):
    id = fields.Int(dump_only=True)
    charity_id = fields.Int(dump_only=True)
    title = fields.Str(required=True, validate=validate.Length(min=3, max=200))
    content = fields.Str(required=True)
    image_url = fields.Url(allow_none=True)
    published = fields.Bool()
    created_at = fields.DateTime(dump_only=True)


class BeneficiarySchema(Schema):
    id = fields.Int(dump_only=True)
    charity_id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=2, max=150))
    age = fields.Int(allow_none=True, validate=validate.Range(min=0, max=150))
    location = fields.Str(allow_none=True)
    story = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class InventoryItemSchema(Schema):
    id = fields.Int(dump_only=True)
    charity_id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    quantity = fields.Int(required=True, validate=validate.Range(min=0))
    unit = fields.Str(allow_none=True)
    notes = fields.Str(allow_none=True)
    updated_at = fields.DateTime(dump_only=True)
