"""Marshmallow schemas for User serialization and validation."""

import re
from marshmallow import Schema, fields, validate, validates, ValidationError, post_load


PHONE_RE = re.compile(r"^\+254[17]\d{8}$")


def validate_password(value: str) -> None:
    if len(value) < 8:
        raise ValidationError("Password must be at least 8 characters.")
    if not re.search(r"\d", value):
        raise ValidationError("Password must contain at least one number.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", value):
        raise ValidationError("Password must contain at least one symbol.")


class RegisterSchema(Schema):
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    email = fields.Email(required=True)
    phone = fields.Str(
        required=False,
        load_default=None,
        validate=validate.Regexp(
            PHONE_RE,
            error="Phone must be in Kenyan format: +254XXXXXXXXX",
        ),
    )
    password = fields.Str(required=True, load_only=True)
    role = fields.Str(
        load_default="donor",
        validate=validate.OneOf(["donor", "charity"]),  # admin created via seed/CLI
    )

    @validates("password")
    def check_password_strength(self, value):
        validate_password(value)


class LoginSchema(Schema):
    """Login accepts email OR phone + password."""
    identifier = fields.Str(required=True)  # email or phone
    password = fields.Str(required=True, load_only=True)


class UpdateMeSchema(Schema):
    full_name = fields.Str(validate=validate.Length(min=2, max=120))
    phone = fields.Str(
        validate=validate.Regexp(
            PHONE_RE,
            error="Phone must be in Kenyan format: +254XXXXXXXXX",
        )
    )
    password = fields.Str(load_only=True)

    @validates("password")
    def check_password_strength(self, value):
        validate_password(value)


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    full_name = fields.Str()
    email = fields.Email()
    phone = fields.Str()
    role = fields.Str()
    created_at = fields.DateTime(dump_only=True)
