"""Tests for environment configuration parsing."""

from app.config import parse_origins


def test_parse_origins_trims_whitespace_and_trailing_slashes():
    raw = " https://tender-hands-1-0-pkmd.vercel.app/ , http://localhost:5173 "
    assert parse_origins(raw) == [
        "https://tender-hands-1-0-pkmd.vercel.app",
        "http://localhost:5173",
    ]


def test_parse_origins_ignores_empty_entries():
    assert parse_origins("https://a.vercel.app,,  ,/") == ["https://a.vercel.app"]
