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

    # C3コミュニティ活動処理部の実装が決まったら、APIのベースURLを設定する。
    COMMUNITY_SERVICE_BASE_URL = os.getenv("COMMUNITY_SERVICE_BASE_URL", "")

    AUTH_COOKIE_NAME = "auth_token"
    REQUIRE_AUTH_TOKEN = os.getenv("REQUIRE_AUTH_TOKEN", "1").lower() not in {
        "0",
        "false",
        "no",
    }
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
