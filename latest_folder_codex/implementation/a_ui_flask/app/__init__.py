# -*- coding: utf-8 -*-
from app.config import Config


def create_app(config_object: type[Config] = Config):
    from flask import Flask

    from app.c1_ui.routes import c1_ui

    app = Flask(__name__)
    app.config.from_object(config_object)
    app.register_blueprint(c1_ui)
    return app
