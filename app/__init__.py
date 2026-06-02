from flask import Flask


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        return "CommunityComposer"

    return app
