"""Shared utilities: error formatting, role decorators."""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.extensions import db


# ---------------------------------------------------------------------------
# Consistent JSON error helper
# ---------------------------------------------------------------------------

def error_response(message: str, status: int = 400, errors: dict | None = None):
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status


def success_response(data, status: int = 200, meta: dict | None = None):
    body = {"success": True, "data": data}
    if meta:
        body["meta"] = meta
    return jsonify(body), status


def current_user_id() -> int:
    """Return the current JWT identity as an integer.

    Flask-JWT-Extended 4.x serializes the identity as a string in the sub
    claim (required by RFC 7519). This helper converts it back to an int
    for use with SQLAlchemy integer primary keys.
    """
    return int(get_jwt_identity())


# ---------------------------------------------------------------------------
# Consistent JSON error helper
# ---------------------------------------------------------------------------

def error_response(message: str, status: int = 400, errors: dict | None = None):
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status


def success_response(data, status: int = 200, meta: dict | None = None):
    body = {"success": True, "data": data}
    if meta:
        body["meta"] = meta
    return jsonify(body), status


# ---------------------------------------------------------------------------
# Role-based access decorators
# ---------------------------------------------------------------------------

def _require_role(*roles):
    """Factory that returns a decorator enforcing one of the given roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            from app.models.user import User  # late import avoids circular deps

            user_id = current_user_id()
            user = db.session.get(User, user_id)
            if user is None:
                return error_response("User not found.", 404)
            if user.role not in roles:
                return error_response("Access denied.", 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


require_donor = _require_role("donor", "admin")
require_charity = _require_role("charity", "admin")
require_admin = _require_role("admin")
require_auth = _require_role("donor", "charity", "admin")
