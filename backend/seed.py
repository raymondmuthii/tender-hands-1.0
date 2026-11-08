"""Seed script: loads 4 charities, 1 admin, 1 donor, and sample donations.

Usage:
    python seed.py
"""

from datetime import date, datetime, timezone
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.charity import Charity
from app.models.donation import Donation, RecurringDonation

app = create_app()

CHARITIES = [
    {
        "slug": "amani",
        "name": "Amani Learning Trust",
        "category": "Education",
        "location": "Kibera, Nairobi",
        "description": (
            "Amani Learning Trust provides quality education to children in Kibera, "
            "one of Africa's largest urban slums. We run three community schools "
            "serving over 1,200 pupils, with trained teachers and modern learning materials."
        ),
        "image_url": "https://images.unsplash.com/photo-1509062522246-3755977927d7?w=800",
        "goal_amount": 2_000_000,
        "is_featured": True,
    },
    {
        "slug": "maji-kwa-wote",
        "name": "Maji Kwa Wote",
        "category": "Clean water",
        "location": "Turkana County",
        "description": (
            "Maji Kwa Wote ('Water for All') drills boreholes and installs solar-powered "
            "pumps in arid Turkana County where communities walk up to 20 km for water. "
            "Each borehole serves 500+ people for 20+ years."
        ),
        "image_url": "https://images.unsplash.com/photo-1541544537156-7627a7a4aa1c?w=800",
        "goal_amount": 3_500_000,
        "is_featured": True,
    },
    {
        "slug": "tumaini-health",
        "name": "Tumaini Health Collective",
        "category": "Healthcare",
        "location": "Kisumu County",
        "description": (
            "Tumaini Health Collective operates mobile health clinics in rural Kisumu, "
            "bringing maternal healthcare, vaccinations, and chronic disease management "
            "to villages without permanent medical facilities."
        ),
        "image_url": "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=800",
        "goal_amount": 1_800_000,
        "is_featured": False,
    },
    {
        "slug": "tupande",
        "name": "Tupande Community",
        "category": "Livelihoods",
        "location": "Meru County",
        "description": (
            "Tupande Community ('Let's Rise Together') supports smallholder farmers in "
            "Meru with training, cooperative marketing, and micro-loans. Over 3,000 "
            "farming families have doubled their incomes since 2018."
        ),
        "image_url": "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?w=800",
        "goal_amount": 1_200_000,
        "is_featured": False,
    },
]

SAMPLE_DONATIONS = [
    {"slug": "amani",          "amount": 5_000},
    {"slug": "maji-kwa-wote",  "amount": 2_500},
    {"slug": "tumaini-health", "amount": 1_000},
    {"slug": "tupande",        "amount": 3_000},
    {"slug": "amani",          "amount": 10_000},
]


def run():
    with app.app_context():
        db.create_all()

        # ----- Admin -----
        admin = User.query.filter_by(email="admin@tenderhands.co.ke").first()
        if not admin:
            admin = User(
                full_name="TH Admin",
                email="admin@tenderhands.co.ke",
                phone="+254700000001",
                role="admin",
            )
            admin.set_password("Admin@1234!")
            db.session.add(admin)
            db.session.flush()
            print("Created admin: admin@tenderhands.co.ke / Admin@1234!")
        else:
            print("Admin already exists – skipping.")

        # ----- Charity owner (needed as owner_id) -----
        owner = User.query.filter_by(email="owner@tenderhands.co.ke").first()
        if not owner:
            owner = User(
                full_name="Charity Owner",
                email="owner@tenderhands.co.ke",
                phone="+254711000001",
                role="charity",
            )
            owner.set_password("Owner@1234!")
            db.session.add(owner)
            db.session.flush()
            print("Created charity owner: owner@tenderhands.co.ke / Owner@1234!")
        else:
            print("Charity owner already exists – skipping.")

        # ----- Demo donor -----
        donor = User.query.filter_by(email="donor@tenderhands.co.ke").first()
        if not donor:
            donor = User(
                full_name="Demo Donor",
                email="donor@tenderhands.co.ke",
                phone="+254722000001",
                role="donor",
            )
            donor.set_password("Donor@1234!")
            db.session.add(donor)
            db.session.flush()
            print("Created donor: donor@tenderhands.co.ke / Donor@1234!")
        else:
            print("Donor already exists – skipping.")

        db.session.commit()

        # ----- Charities -----
        charity_map = {}
        for c_data in CHARITIES:
            charity = Charity.query.filter_by(slug=c_data["slug"]).first()
            if not charity:
                charity = Charity(
                    owner_id=owner.id,
                    status="approved",
                    **c_data,
                )
                db.session.add(charity)
                print(f"Created charity: {c_data['name']}")
            else:
                print(f"Charity '{c_data['slug']}' already exists – skipping.")
            charity_map[c_data["slug"]] = charity

        db.session.commit()
        # Refresh map after commit so IDs are populated
        charity_map = {
            c["slug"]: Charity.query.filter_by(slug=c["slug"]).first()
            for c in CHARITIES
        }

        # ----- Sample donations -----
        existing_donations = Donation.query.filter_by(user_id=donor.id).count()
        if existing_donations == 0:
            for idx, d in enumerate(SAMPLE_DONATIONS):
                charity = charity_map[d["slug"]]
                donation = Donation(
                    user_id=donor.id,
                    charity_id=charity.id,
                    amount=d["amount"],
                    phone=donor.phone,
                    mpesa_receipt=f"QHX{100 + idx}DEMO",
                    status="completed",
                )
                db.session.add(donation)
            print("Created 5 sample donations for demo donor.")
        else:
            print("Donations already exist – skipping.")

        # ----- Sample recurring donation -----
        existing_rec = RecurringDonation.query.filter_by(user_id=donor.id).count()
        if existing_rec == 0:
            amani = charity_map["amani"]
            rec = RecurringDonation(
                user_id=donor.id,
                charity_id=amani.id,
                amount=1_000,
                frequency="monthly",
                next_run_date=date(2026, 12, 1),
                status="active",
            )
            db.session.add(rec)
            print("Created 1 sample recurring donation.")
        else:
            print("Recurring donations already exist – skipping.")

        db.session.commit()
        print("\nSeed complete.")


if __name__ == "__main__":
    run()
