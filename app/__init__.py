"""Flask application factory."""

from __future__ import annotations

from flask import Flask

from app.core.config import DevelopmentConfig
from app.routes import blackjack_bp, poker_bp


def create_app(config_object: type | None = None) -> Flask:
    """Flask application factory."""
    app = Flask(__name__)
    config = config_object or DevelopmentConfig
    app.config.from_object(config)

    app.register_blueprint(poker_bp)
    app.register_blueprint(blackjack_bp)

    @app.after_request
    def add_cors_headers(response):  # type: ignore[override]
        origin = app.config.get("CORS_ALLOW_ORIGINS", "*")
        response.headers.setdefault("Access-Control-Allow-Origin", origin)
        response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.setdefault("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        return response

    return app


__all__ = ["create_app"]
