"""Tests for admin endpoints: charity approval, rejection, feature toggle, stats."""

import pytest
from app.models.charity import Charity


class TestAdminCharityApproval:
    def _pending_charity(self, db, charity_user, slug="admin-pending"):
        c = Charity(
            slug=slug,
            name=f"Org {slug}",
            category="Education",
            location="Nairobi",
            description="A pending charity for admin testing purposes only.",
            goal_amount=100_000,
            owner_id=charity_user.id,
            status="pending",
        )
        db.session.add(c)
        db.session.commit()
        return c

    def test_approve_charity(self, client, db, charity_user, admin_tokens):
        charity = self._pending_charity(db, charity_user, "to-approve")
        access, _ = admin_tokens
        resp = client.post(
            f"/api/admin/charities/{charity.slug}/approve",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        db.session.refresh(charity)
        assert charity.status == "approved"

    def test_reject_charity(self, client, db, charity_user, admin_tokens):
        charity = self._pending_charity(db, charity_user, "to-reject")
        access, _ = admin_tokens
        resp = client.post(
            f"/api/admin/charities/{charity.slug}/reject",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        db.session.refresh(charity)
        assert charity.status == "rejected"

    def test_feature_toggle(self, client, db, charity_user, admin_tokens):
        charity = self._pending_charity(db, charity_user, "to-feature")
        access, _ = admin_tokens

        # Toggle on
        resp = client.post(
            f"/api/admin/charities/{charity.slug}/feature",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["is_featured"] is True

        # Toggle off
        resp2 = client.post(
            f"/api/admin/charities/{charity.slug}/feature",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp2.get_json()["data"]["is_featured"] is False

    def test_list_charities_filtered_by_status(self, client, db, charity_user, admin_tokens):
        self._pending_charity(db, charity_user, "list-pending-1")
        access, _ = admin_tokens
        resp = client.get(
            "/api/admin/charities?status=pending",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert all(c["status"] == "pending" for c in data)

    def test_admin_denied_for_donor(self, client, donor_tokens):
        access, _ = donor_tokens
        resp = client.get(
            "/api/admin/charities",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 403

    def test_admin_denied_for_unauthenticated(self, client, db):
        resp = client.get("/api/admin/charities")
        assert resp.status_code == 401


class TestAdminStats:
    def test_stats_returns_expected_keys(self, client, admin_tokens):
        access, _ = admin_tokens
        resp = client.get(
            "/api/admin/stats",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        for key in (
            "total_users",
            "total_charities",
            "pending_charities",
            "approved_charities",
            "total_donations",
            "total_raised_kes",
        ):
            assert key in data, f"Missing key: {key}"
