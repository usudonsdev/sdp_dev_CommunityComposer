import os
from flask import Flask

from dotenv import load_dotenv

from app.extensions import db
from app.routes.communities import communities_bp
from app.routes.users import users_bp


def _env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    return value.strip()


def create_app(config: dict | None = None) -> Flask:
    """Flask アプリケーションを生成して設定する。"""
    
    load_dotenv()
    
    app = Flask(__name__)
    
    app.config["GOOGLE_CLIENT_ID"] = _env("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_CLIENT_SECRET"] = _env("GOOGLE_CLIENT_SECRET")

# -------------------------------------------------------------
    # セキュリティ修正: 環境変数から重要なキーを設定
    # -------------------------------------------------------------
    
    # セッション暗号化用のシークレットキーを設定（未設定ならローカル用にデフォ値を付与）
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-me-in-production")
    
    # 本番環境（FLASK_ENVではない本番運用時）での設定漏れを防ぐ防衛策
    if os.getenv("FLASK_ENV") == "production" and app.config["SECRET_KEY"] == "dev-secret-key-change-me-in-production":
        raise ValueError("本番環境では必ず安全な SECRET_KEY を環境変数に設定してください！")

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="sqlite:///app.sqlite3",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        ADMIN_LOGIN_SECRET=None,
    )
    if config:
        app.config.update(config)

    # リクエスト処理の前に、共通拡張と機能別 Blueprint を登録する。
    db.init_app(app)
    app.register_blueprint(users_bp)
    app.register_blueprint(communities_bp)

    # 開発環境とテスト環境では、テーブルを自動生成する。
    with app.app_context():
        db.create_all()

    @app.get("/")
    def index() -> str:
        return "CommunityComposer"

    return app
