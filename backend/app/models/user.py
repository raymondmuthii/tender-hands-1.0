"""User model."""

import re
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(
        db.Enum("donor", "charity", "admin", name="user_roles"),
        nullable=False,
        default="donor",
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    charities = db.relationship("Charity", back_populates="owner", lazy="dynamic")
    donations = db.relationship("Donation", back_populates="user", lazy="dynamic")
    recurring_donations = db.relationship(
        "RecurringDonation", back_populates="user", lazy="dynamic"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize a Kenyan phone number to +254XXXXXXXXX format."""
        digits = re.sub(r"\D", "", phone)
        if digits.startswith("254") and len(digits) == 12:
            return f"+{digits}"
        if digits.startswith("0") and len(digits) == 10:
            return f"+254{digits[1:]}"
        if len(digits) == 9:
            return f"+254{digits}"
        return phone  # return as-is; validation schema catches invalid values

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"
