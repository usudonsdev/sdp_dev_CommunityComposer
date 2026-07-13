# -*- coding: utf-8 -*-
import os


_PLACEHOLDER_VALUES = {
    "",
    "your_google_client_id_here",
    "your_google_client_secret_here",
    "dummy-id",
    "dummy",
    "ここにクライアントシークレットを貼り付け",
}


def _is_configured_oauth_value(value: str | None) -> bool:
    if not value:
        return False
    return value.strip() not in _PLACEHOLDER_VALUES


def config_flag(value, *, default: bool = False) -> bool:
    """環境変数や app.config の値を bool に正規化する（"0" は False）."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    return default


def _resolve_auth_mock_enabled() -> bool:
    """OAuth クライアント情報が揃っていれば Google 認証、未設定ならモック認証."""
    explicit = os.getenv("AUTH_MOCK_ENABLED")
    if explicit is not None and explicit.strip() != "":
        return config_flag(explicit, default=True)

    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    return not (
        _is_configured_oauth_value(client_id)
        and _is_configured_oauth_value(client_secret)
    )


def resolve_auth_mock_enabled_for_app(app) -> bool:
    """load_dotenv 後の app.config から認証モードを決定する."""
    explicit = os.getenv("AUTH_MOCK_ENABLED")
    if explicit is not None and explicit.strip() != "":
        return config_flag(explicit, default=True)

    client_id = app.config.get("GOOGLE_CLIENT_ID", "")
    client_secret = app.config.get("GOOGLE_CLIENT_SECRET", "")
    return not (
        _is_configured_oauth_value(client_id)
        and _is_configured_oauth_value(client_secret)
    )


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-key")

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
    AUTH_REGISTER_ENDPOINT = os.getenv("AUTH_REGISTER_ENDPOINT", "/auth/register")
    AUTH_VERIFY_ENDPOINT = os.getenv("AUTH_VERIFY_ENDPOINT", "/auth/verify")
    AUTH_ADMIN_LOGIN_ENDPOINT = os.getenv(
        "AUTH_ADMIN_LOGIN_ENDPOINT",
        "/admin/auth/login",
    )
    AUTH_ADMIN_REGISTER_ENDPOINT = os.getenv(
        "AUTH_ADMIN_REGISTER_ENDPOINT",
        "/admin/auth/register",
    )
    AUTH_ADMIN_SECRET = os.getenv("AUTH_ADMIN_SECRET", "")
    AUTH_MOCK_ENABLED = _resolve_auth_mock_enabled()
    AUTH_MOCK_USER_ID = os.getenv("AUTH_MOCK_USER_ID", "1")
    AUTH_MOCK_USER_EMAIL = os.getenv(
        "AUTH_MOCK_USER_EMAIL",
        "student@shibaura-it.ac.jp",
    )
    AUTH_MOCK_ADMIN_USER_ID = os.getenv("AUTH_MOCK_ADMIN_USER_ID", "2")
    AUTH_MOCK_ADMIN_EMAIL = os.getenv(
        "AUTH_MOCK_ADMIN_EMAIL",
        "adminAL24000@shibaura-it.ac.jp",
    )
    AUTH_ADMIN_EMAILS = os.getenv(
        "AUTH_ADMIN_EMAILS",
        "adminAL24000@shibaura-it.ac.jp,admin@shibaura-it.ac.jp",
    )

    COMMUNITY_SERVICE_BASE_URL = os.getenv("COMMUNITY_SERVICE_BASE_URL", "")
    COMMUNITY_CREATOR_USER_ID = os.getenv("COMMUNITY_CREATOR_USER_ID", "")

    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_OAUTH_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")
    GOOGLE_OAUTH_ADMIN_REDIRECT_URI = os.getenv("GOOGLE_OAUTH_ADMIN_REDIRECT_URI", "")
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
    GOOGLE_HOSTED_DOMAIN = os.getenv("GOOGLE_HOSTED_DOMAIN", "shibaura-it.ac.jp")

    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "")
    AUTH_MAGIC_LINK_ENABLED = os.getenv("AUTH_MAGIC_LINK_ENABLED", "")
    AUTH_PASSWORD_ENABLED = os.getenv("AUTH_PASSWORD_ENABLED", "")

    AUTH_MAGIC_LINK_ENDPOINT = os.getenv("AUTH_MAGIC_LINK_ENDPOINT", "/auth/magic-link")
    AUTH_MAGIC_LINK_VERIFY_ENDPOINT = os.getenv(
        "AUTH_MAGIC_LINK_VERIFY_ENDPOINT",
        "/auth/magic-link/verify",
    )
    AUTH_ADMIN_MAGIC_LINK_ENDPOINT = os.getenv(
        "AUTH_ADMIN_MAGIC_LINK_ENDPOINT",
        "/admin/auth/magic-link",
    )
    AUTH_ADMIN_MAGIC_LINK_VERIFY_ENDPOINT = os.getenv(
        "AUTH_ADMIN_MAGIC_LINK_VERIFY_ENDPOINT",
        "/admin/auth/magic-link/verify",
    )

    AUTH_COOKIE_NAME = "auth_token"
    REQUIRE_AUTH_TOKEN = os.getenv("REQUIRE_AUTH_TOKEN", "1").lower() not in {
        "0",
        "false",
        "no",
    }
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
