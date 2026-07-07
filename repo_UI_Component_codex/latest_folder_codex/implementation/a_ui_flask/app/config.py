# -*- coding: utf-8 -*-
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-key")

    # C2認証処理部の実装が決まったら、Google認証開始先URLに差し替える。
    AUTH_GOOGLE_LOGIN_URL = os.getenv(
        "AUTH_GOOGLE_LOGIN_URL",
        "/not-implemented/c2/google-login",
    )
    AUTH_ADMIN_GOOGLE_LOGIN_URL = os.getenv(
        "AUTH_ADMIN_GOOGLE_LOGIN_URL",
        "/not-implemented/c2/admin-google-login",
    )
    AUTH_SERVICE_BASE_URL = os.getenv("AUTH_SERVICE_BASE_URL", "")
    AUTH_LOGIN_ENDPOINT = os.getenv("AUTH_LOGIN_ENDPOINT", "/auth/login")
    AUTH_ADMIN_LOGIN_ENDPOINT = os.getenv(
        "AUTH_ADMIN_LOGIN_ENDPOINT",
        "/admin/auth/login",
    )
    AUTH_ADMIN_SECRET = os.getenv("AUTH_ADMIN_SECRET", "")
    AUTH_MOCK_ENABLED = os.getenv("AUTH_MOCK_ENABLED", "1").lower() not in {
        "0",
        "false",
        "no",
    }
    AUTH_MOCK_USER_ID = os.getenv("AUTH_MOCK_USER_ID", "1")
    AUTH_MOCK_USER_EMAIL = os.getenv(
        "AUTH_MOCK_USER_EMAIL",
        "student@shibaura-it.ac.jp",
    )
    AUTH_MOCK_ADMIN_USER_ID = os.getenv("AUTH_MOCK_ADMIN_USER_ID", "2")
    AUTH_MOCK_ADMIN_EMAIL = os.getenv(
        "AUTH_MOCK_ADMIN_EMAIL",
        "admin@shibaura-it.ac.jp",
    )

    # C3コミュニティ活動処理部の実装が決まったら、APIのベースURLを設定する。
    COMMUNITY_SERVICE_BASE_URL = os.getenv("COMMUNITY_SERVICE_BASE_URL", "")
    COMMUNITY_CREATOR_USER_ID = os.getenv("COMMUNITY_CREATOR_USER_ID", "")

    AUTH_COOKIE_NAME = "auth_token"
    REQUIRE_AUTH_TOKEN = os.getenv("REQUIRE_AUTH_TOKEN", "1").lower() not in {
        "0",
        "false",
        "no",
    }
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
