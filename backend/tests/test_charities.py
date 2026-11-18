"""Tests for charity listing, filtering, and application."""

import pytest
from app.models.charity import Charity, ImpactStory


class TestCharityList:
    def test_list_returns_only_approved(self, client, db, approved_charity, charity_user):
        # Add a pending charity
        pending = Charity(
            slug="pending-charity",
            name="Pending Org",
            category="Healthcare",
            location="Mombasa",
            description="A pending charity awaiting review by the admin team.",
            goal_amount=100_000,
            owner_id=charity_user.id,
            status="pending",
        )
        db.session.add(pending)
        db.session.commit()

        resp = client.get("/api/charities")
        assert resp.status_code == 200
        slugs = [c["id"] for c in resp.get_json()["data"]]
        assert "test-charity" in slugs
        assert "pending-charity" not in slugs

    def test_filter_by_category(self, client, db, approved_charity, charity_user):
        water = Charity(
            slug="water-org",
            name="Water Org",
            category="Clean water",
            location="Turkana",
            description="Providing clean water access to remote communities in Turkana County.",
            goal_amount=200_000,
            owner_id=charity_user.id,
            status="approved",
        )
        db.session.add(water)
        db.session.commit()

        resp = client.get("/api/charities?category=Education")
        data = resp.get_json()["data"]
        assert all(c["category"] == "Education" for c in data)

    def test_filter_by_featured(self, client, db, charity_user):
        featured = Charity(
            slug="featured-org",
            name="Featured Org",
            category="Healthcare",
            location="Kisumu",
            description="A featured healthcare charity that helps rural communities.",
            goal_amount=300_000,
            owner_id=charity_user.id,
            status="approved",
            is_featured=True,
        )
        db.session.add(featured)
        db.session.commit()

        resp = client.get("/api/charities?featured=true")
        data = resp.get_json()["data"]
        assert all(c["is_featured"] is True for c in data)

    def test_search(self, client, approved_charity):
        resp = client.get("/api/charities?search=Test")
        data = resp.get_json()["data"]
        assert any("Test" in c["name"] for c in data)

    def test_pagination_meta(self, client, approved_charity):
        resp = client.get("/api/charities?page=1&per_page=5")
        meta = resp.get_json()["meta"]
        assert "total" in meta
        assert "pages" in meta

    def test_charity_schema_fields(self, client, approved_charity):
        resp = client.get("/api/charities")
        charity = resp.get_json()["data"][0]
        for field in ("id", "name", "category", "location", "description", "amount", "goal", "image"):
            assert field in charity, f"Missing field: {field}"
        # id should be the slug string, not an integer
        assert isinstance(charity["id"], str)

    def test_get_charity_detail(self, client, approved_charity):
        resp = client.get("/api/charities/test-charity")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["id"] == "test-charity"

    def test_get_charity_not_found(self, client, db):
        resp = client.get("/api/charities/does-not-exist")
        assert resp.status_code == 404

    def test_pending_charity_hidden_from_public(self, client, db, charity_user):
        pending = Charity(
            slug="hidden-pending",
            name="Hidden Pending",
            category="Education",
            location="Nairobi",
            description="This charity is pending and should not be publicly visible.",
            goal_amount=50_000,
            owner_id=charity_user.id,
            status="pending",
        )
        db.session.add(pending)
        db.session.commit()

        resp = client.get("/api/charities/hidden-pending")
        assert resp.status_code == 404


class TestCharityApplication:
    def test_create_charity_requires_charity_role(self, client, donor_user, donor_tokens):
        access, _ = donor_tokens
        resp = client.post(
            "/api/charities",
            json={
                "name": "New Org",
                "slug": "new-org",
                "category": "Education",
                "location": "Nairobi",
                "description": "A new charity applying for approval on the platform.",
                "goal_amount": 100_000,
            },
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 403

    def test_create_charity_as_charity_owner(self, client, charity_user, charity_tokens):
        access, _ = charity_tokens
        resp = client.post(
            "/api/charities",
            json={
                "name": "Brand New Org",
                "slug": "brand-new-org",
                "category": "Healthcare",
                "location": "Kisumu",
                "description": "A brand new healthcare organisation applying to join the platform.",
                "goal_amount": 500_000,
            },
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["status"] == "pending"

    def test_update_charity_by_owner(self, client, approved_charity, charity_tokens):
        access, _ = charity_tokens
        resp = client.patch(
            "/api/charities/test-charity",
            json={"location": "Mombasa"},
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["location"] == "Mombasa"

    def test_update_charity_denied_for_other_user(
        self, client, approved_charity, donor_tokens
    ):
        access, _ = donor_tokens
        resp = client.patch(
            "/api/charities/test-charity",
            json={"location": "Mombasa"},
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 403


class TestMyCharity:
    """GET /api/charities/mine – used by the owner dashboard."""

    def test_returns_the_owners_charity(self, client, approved_charity, charity_tokens):
        access, _ = charity_tokens
        resp = client.get(
            "/api/charities/mine",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["id"] == "test-charity"
        assert data["status"] == "approved"

    def test_returns_null_before_applying(self, client, charity_user, charity_tokens):
        access, _ = charity_tokens
        resp = client.get(
            "/api/charities/mine",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"] is None

    def test_returns_pending_charity_while_awaiting_review(
        self, client, db, charity_user, charity_tokens
    ):
        pending = Charity(
            slug="awaiting-review",
            name="Awaiting Review",
            category="Livelihoods",
            location="Nakuru",
            description="A charity application that is waiting for admin review.",
            goal_amount=80_000,
            owner_id=charity_user.id,
            status="pending",
        )
        db.session.add(pending)
        db.session.commit()

        access, _ = charity_tokens
        resp = client.get(
            "/api/charities/mine",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.get_json()["data"]["status"] == "pending"

    def test_requires_charity_role(self, client, donor_tokens):
        access, _ = donor_tokens
        resp = client.get(
            "/api/charities/mine",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 403

    def test_requires_auth(self, client, db):
        assert client.get("/api/charities/mine").status_code == 401


class TestStoryVisibility:
    """Public sees published stories only; the owner can ask for drafts."""

    def _draft_story(self, db, charity):
        story = ImpactStory(
            charity_id=charity.id,
            title="A draft impact story",
            content="Not published yet.",
            published=False,
        )
        db.session.add(story)
        db.session.commit()
        return story

    def test_public_list_hides_drafts(self, client, db, approved_charity):
        self._draft_story(db, approved_charity)
        resp = client.get("/api/charities/test-charity/stories")
        assert resp.get_json()["data"] == []

    def test_owner_can_list_drafts(self, client, db, approved_charity, charity_tokens):
        self._draft_story(db, approved_charity)
        access, _ = charity_tokens
        resp = client.get(
            "/api/charities/test-charity/stories?all=1",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert len(resp.get_json()["data"]) == 1

    def test_donor_cannot_list_drafts(self, client, db, approved_charity, donor_tokens):
        self._draft_story(db, approved_charity)
        access, _ = donor_tokens
        resp = client.get(
            "/api/charities/test-charity/stories?all=1",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.get_json()["data"] == []
