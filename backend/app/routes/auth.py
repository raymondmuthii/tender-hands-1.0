"""Authentication routes: register, login, refresh, me."""

from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from marshmallow import ValidationError

from app.extensions import db
from app.models.user import User
from app.schemas.user_schema import RegisterSchema, LoginSchema, UpdateMeSchema, UserSchema
from app.utils import error_response, success_response, require_auth, current_user_id

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_register_schema = RegisterSchema()
_login_schema = LoginSchema()
_update_schema = UpdateMeSchema()
_user_schema = UserSchema()


@auth_bp.post("/register")
def register():
    json_data = request.get_json(silent=True) or {}
    try:
        data = _register_schema.load(json_data)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    # Normalise phone if provided
    if data.get("phone"):
        data["phone"] = User.normalize_phone(data["phone"])

    if User.query.filter_by(email=data["email"]).first():
        return error_response("Email already registered.", 409)

    if data.get("phone") and User.query.filter_by(phone=data["phone"]).first():
        return error_response("Phone number already registered.", 409)

    user = User(
        full_name=data["full_name"],
        email=data["email"],
        phone=data.get("phone"),
        role=data.get("role", "donor"),
    )
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return success_response(
        {
            "user": _user_schema.dump(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
        201,
    )


@auth_bp.post("/login")
def login():
    json_data = request.get_json(silent=True) or {}
    try:
        data = _login_schema.load(json_data)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    identifier = data["identifier"].strip()
    password = data["password"]

    # Decide whether identifier is an email or a phone number
    if "@" in identifier:
        user = User.query.filter_by(email=identifier.lower()).first()
    else:
        normalized = User.normalize_phone(identifier)
        user = User.query.filter_by(phone=normalized).first()

    if not user or not user.check_password(password):
        return error_response("Invalid credentials.", 401)

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return success_response(
        {
            "user": _user_schema.dump(user),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    )


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    # Preserve the string identity as-is for the new access token
    user_id_str = get_jwt_identity()
    access_token = create_access_token(identity=user_id_str)
    return success_response({"access_token": access_token})


@auth_bp.get("/me")
@require_auth
def me():
    user_id = current_user_id()
    user = db.session.get(User, user_id)
    if not user:
        return error_response("User not found.", 404)
    return success_response(_user_schema.dump(user))


@auth_bp.patch("/me")
@require_auth
def update_me():
    user_id = current_user_id()
    user = db.session.get(User, user_id)
    if not user:
        return error_response("User not found.", 404)

    json_data = request.get_json(silent=True) or {}
    try:
        data = _update_schema.load(json_data)
    except ValidationError as err:
        return error_response("Validation failed.", 422, err.messages)

    if "full_name" in data:
        user.full_name = data["full_name"]

    if "phone" in data:
        normalized = User.normalize_phone(data["phone"])
        existing = User.query.filter_by(phone=normalized).first()
        if existing and existing.id != user.id:
            return error_response("Phone number already in use.", 409)
        user.phone = normalized

    if "password" in data:
        user.set_password(data["password"])

    db.session.commit()
    return success_response(_user_schema.dump(user))
