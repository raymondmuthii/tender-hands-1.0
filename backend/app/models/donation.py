"""Donation and RecurringDonation models."""

from datetime import datetime, timezone
from app.extensions import db


class Donation(db.Model):
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    charity_id = db.Column(db.Integer, db.ForeignKey("charities.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # KES
    payment_method = db.Column(
        db.String(20), nullable=False, default="M-PESA"
    )
    mpesa_receipt = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    # checkout_request_id links the STK push to this donation for the callback
    checkout_request_id = db.Column(db.String(100), nullable=True, index=True)
    status = db.Column(
        db.Enum("pending", "completed", "failed", name="donation_statuses"),
        nullable=False,
        default="pending",
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = db.relationship("User", back_populates="donations")
    charity = db.relationship("Charity", back_populates="donations")

    def __repr__(self) -> str:
        return f"<Donation {self.id} KES {self.amount} [{self.status}]>"


class RecurringDonation(db.Model):
    __tablename__ = "recurring_donations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    charity_id = db.Column(db.Integer, db.ForeignKey("charities.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # KES
    frequency = db.Column(
        db.Enum("monthly", name="recurring_frequencies"),
        nullable=False,
        default="monthly",
    )
    next_run_date = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum("active", "paused", "cancelled", name="recurring_statuses"),
        nullable=False,
        default="active",
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = db.relationship("User", back_populates="recurring_donations")
    charity = db.relationship("Charity", back_populates="recurring_donations")

    def __repr__(self) -> str:
        return f"<RecurringDonation {self.id} KES {self.amount} {self.frequency}>"
