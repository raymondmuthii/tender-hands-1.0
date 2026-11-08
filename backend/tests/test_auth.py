"""Tests for authentication endpoints."""

import pytest


class TestRegister:
    def test_register_success(self, client, db):
        resp = client.post(
            "/api/auth/register",
            json={
                "full_name": "Jane Doe",
                "email": "jane@example.com",
                "password": "Secret@99",
                "role": "donor",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["user"]["email"] == "jane@example.com"
        assert "access_token" in data["data"]

    def test_register_duplicate_email(self, client, donor_user):
        resp = client.post(
            "/api/auth/register",
            json={
                "full_name": "Clone",
                "email": "donor@test.com",
                "password": "Secret@99",
            },
        )
        assert resp.status_code == 409

    def test_register_weak_password_no_number(self, client, db):
        resp = client.post(
            "/api/auth/register",
            json={
                "full_name": "Bad Pass",
                "email": "bad@example.com",
                "password": "NoNumber!",
            },
        )
        assert resp.status_code == 422

    def test_register_weak_password_no_symbol(self, client, db):
        resp = client.post(
            "/api/auth/register",
            json={
                "full_name": "Bad Pass",
                "email": "bad@example.com",
                "password": "NoSymbol12",
            },
        )
        assert resp.status_code == 422

    def test_register_weak_password_too_short(self, client, db):
        resp = client.post(
            "/api/auth/register",
            json={
                "full_name": "Bad Pass",
                "email": "bad@example.com",
                "password": "Sh@1",
            },
        )
        assert resp.status_code == 422

    def test_register_invalid_phone(self, client, db):
        resp = client.post(
            "/api/auth/register",
            json={
                "full_name": "Phone Test",
                "email": "phone@example.com",
                "password": "Valid@123",
                "phone": "08001234",  # not Kenyan format
            },
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_with_email(self, client, donor_user):
        resp = client.post(
            "/api/auth/login",
            json={"identifier": "donor@test.com", "password": "Donor@1234!"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "access_token" in data["data"]

    def test_login_with_phone(self, client, donor_user):
        resp = client.post(
            "/api/auth/login",
            json={"identifier": "+254722000099", "password": "Donor@1234!"},
        )
        assert resp.status_code == 200

    def test_login_wrong_password(self, client, donor_user):
        resp = client.post(
            "/api/auth/login",
            json={"identifier": "donor@test.com", "password": "WrongPass@1"},
        )
        assert resp.status_code == 401

    def test_login_unknown_email(self, client, db):
        resp = client.post(
            "/api/auth/login",
            json={"identifier": "ghost@example.com", "password": "Ghost@123"},
        )
        assert resp.status_code == 401


class TestMe:
    def test_get_me(self, client, donor_user, donor_tokens):
        access, _ = donor_tokens
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["email"] == "donor@test.com"

    def test_get_me_no_token(self, client, db):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_update_me(self, client, donor_user, donor_tokens):
        access, _ = donor_tokens
        resp = client.patch(
            "/api/auth/me",
            json={"full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {access}"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["full_name"] == "Updated Name"


class TestRefresh:
    def test_refresh(self, client, donor_user, donor_tokens):
        _, refresh = donor_tokens
        resp = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {refresh}"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()["data"]
