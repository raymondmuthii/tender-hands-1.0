"""Charity model and related sub-models."""

from datetime import datetime, timezone
from app.extensions import db


class Charity(db.Model):
    __tablename__ = "charities"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(
        db.Enum(
            "Education",
            "Clean water",
            "Healthcare",
            "Livelihoods",
            name="charity_categories",
        ),
        nullable=False,
    )
    location = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    goal_amount = db.Column(db.Integer, nullable=False, default=0)  # KES
    status = db.Column(
        db.Enum("pending", "approved", "rejected", name="charity_statuses"),
        nullable=False,
        default="pending",
    )
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    owner = db.relationship("User", back_populates="charities")
    donations = db.relationship("Donation", back_populates="charity", lazy="dynamic")
    recurring_donations = db.relationship(
        "RecurringDonation", back_populates="charity", lazy="dynamic"
    )
    impact_stories = db.relationship(
        "ImpactStory", back_populates="charity", lazy="dynamic", cascade="all, delete-orphan"
    )
    beneficiaries = db.relationship(
        "Beneficiary", back_populates="charity", lazy="dynamic", cascade="all, delete-orphan"
    )
    inventory_items = db.relationship(
        "InventoryItem", back_populates="charity", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def amount_raised(self) -> int:
        """Sum of all completed donations for this charity."""
        from app.models.donation import Donation  # avoid circular import at module load

        result = (
            db.session.query(db.func.coalesce(db.func.sum(Donation.amount), 0))
            .filter(
                Donation.charity_id == self.id,
                Donation.status == "completed",
            )
            .scalar()
        )
        return int(result)

    def __repr__(self) -> str:
        return f"<Charity {self.slug}>"


class ImpactStory(db.Model):
    __tablename__ = "impact_stories"

    id = db.Column(db.Integer, primary_key=True)
    charity_id = db.Column(db.Integer, db.ForeignKey("charities.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    published = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    charity = db.relationship("Charity", back_populates="impact_stories")

    def __repr__(self) -> str:
        return f"<ImpactStory {self.id} for charity {self.charity_id}>"


class Beneficiary(db.Model):
    __tablename__ = "beneficiaries"

    id = db.Column(db.Integer, primary_key=True)
    charity_id = db.Column(db.Integer, db.ForeignKey("charities.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(150), nullable=True)
    story = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    charity = db.relationship("Charity", back_populates="beneficiaries")

    def __repr__(self) -> str:
        return f"<Beneficiary {self.name}>"


class InventoryItem(db.Model):
    __tablename__ = "inventory_items"

    id = db.Column(db.Integer, primary_key=True)
    charity_id = db.Column(db.Integer, db.ForeignKey("charities.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    unit = db.Column(db.String(50), nullable=True)  # e.g. "books", "kg", "units"
    notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    charity = db.relationship("Charity", back_populates="inventory_items")

    def __repr__(self) -> str:
        return f"<InventoryItem {self.name} x{self.quantity}>"
