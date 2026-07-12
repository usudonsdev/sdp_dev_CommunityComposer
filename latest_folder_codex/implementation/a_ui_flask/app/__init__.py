# -*- coding: utf-8 -*-
import os
from pathlib import Path

from dotenv import load_dotenv

from app.config import Config


def _apply_env_config(app) -> None:
    for key in (
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "SECRET_KEY",
        "PUBLIC_BASE_URL",
        "GOOGLE_OAUTH_REDIRECT_URI",
        "GOOGLE_OAUTH_ADMIN_REDIRECT_URI",
        "GOOGLE_HOSTED_DOMAIN",
        "AUTH_MOCK_ENABLED",
    ):
        value = os.getenv(key)
        if value is not None:
            app.config[key] = value.strip()

    public_base_url = app.config.get("PUBLIC_BASE_URL", "")
    if isinstance(public_base_url, str) and public_base_url.startswith("https://"):
        app.config["PREFERRED_URL_SCHEME"] = "https"


def create_app(config_object: type[Config] = Config):
    from flask import Flask

    from app.c1_ui.routes import c1_ui

    repo_root = Path(__file__).resolve().parents[4]
    load_dotenv(repo_root / ".env")

    app = Flask(__name__)
    app.config.from_object(config_object)
    _apply_env_config(app)
    app.register_blueprint(c1_ui)
    return app
