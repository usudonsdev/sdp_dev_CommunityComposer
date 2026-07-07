# -*- coding: utf-8 -*-
import os
from pathlib import Path

from dotenv import load_dotenv

from app.config import Config


def _apply_env_config(app) -> None:
    for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "SECRET_KEY"):
        value = os.getenv(key)
        if value is not None:
            app.config[key] = value.strip()


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
