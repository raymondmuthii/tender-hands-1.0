"""Marshmallow schemas for Donation and RecurringDonation."""

from marshmallow import Schema, fields, validate
from datetime import date


class CreateDonationSchema(Schema):
    charity_id = fields.Str(required=True)  # slug
    amount = fields.Int(required=True, validate=validate.Range(min=10))  # min KES 10
    phone = fields.Str(required=True)


class DonationSchema(Schema):
    id = fields.Int(dump_only=True)
    charity_id = fields.Int(dump_only=True)
    charity_name = fields.Str(dump_only=True)  # populated manually
    amount = fields.Int(dump_only=True)
    payment_method = fields.Str(dump_only=True)
    mpesa_receipt = fields.Str(dump_only=True)
    phone = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class DonationReceiptSchema(Schema):
    id = fields.Int()
    charity_name = fields.Str()
    amount = fields.Int()
    mpesa_receipt = fields.Str()
    phone = fields.Str()
    status = fields.Str()
    created_at = fields.DateTime()


class CreateRecurringSchema(Schema):
    charity_id = fields.Str(required=True)  # slug
    amount = fields.Int(required=True, validate=validate.Range(min=10))
    frequency = fields.Str(
        load_default="monthly", validate=validate.OneOf(["monthly"])
    )
    next_run_date = fields.Date(required=True)


class UpdateRecurringSchema(Schema):
    amount = fields.Int(validate=validate.Range(min=10))
    status = fields.Str(validate=validate.OneOf(["active", "paused", "cancelled"]))
    next_run_date = fields.Date()


class RecurringDonationSchema(Schema):
    id = fields.Int(dump_only=True)
    charity_id = fields.Int(dump_only=True)
    charity_name = fields.Str(dump_only=True)  # populated manually
    amount = fields.Int(dump_only=True)
    frequency = fields.Str(dump_only=True)
    next_run_date = fields.Date(dump_only=True)
    status = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
