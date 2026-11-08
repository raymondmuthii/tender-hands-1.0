"""Flask application factory."""

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager

from app.config import get_config
from app.extensions import db, migrate, jwt, cors


def create_app(config_override: object | None = None) -> Flask:
    app = Flask(__name__)

    # Load config
    app.config.from_object(get_config())
    if config_override:
        app.config.from_object(config_override)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # Import models so Alembic / Flask-Migrate can detect them
    with app.app_context():
        from app import models  # noqa: F401

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.charities import charities_bp
    from app.routes.donations import donations_bp
    from app.routes.recurring import recurring_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.admin import admin_bp

    for bp in (auth_bp, charities_bp, donations_bp, recurring_bp, dashboard_bp, admin_bp):
        app.register_blueprint(bp)

    # -----------------------------------------------------------------------
    # JWT error handlers – consistent JSON shape
    # -----------------------------------------------------------------------

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"success": False, "message": "Token has expired."}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"success": False, "message": "Invalid token."}), 422

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"success": False, "message": "Authorization token required."}), 401

    # -----------------------------------------------------------------------
    # Generic error handlers
    # -----------------------------------------------------------------------

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Resource not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success": False, "message": "Method not allowed."}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"success": False, "message": "Internal server error."}), 500

    return app
