# -*- coding: utf-8 -*-
import pytest

from app import create_app


@pytest.mark.email_auth
def test_google_oauth_configured_in_app(google_oauth_credentials):
    app = create_app()
    app.config.update(
        GOOGLE_CLIENT_ID=google_oauth_credentials["client_id"],
        GOOGLE_CLIENT_SECRET=google_oauth_credentials["client_secret"],
        AUTH_MOCK_ENABLED=False,
        SERVER_NAME="localhost",
        PREFERRED_URL_SCHEME="http",
    )

    with app.app_context():
        from app.c1_ui.google_oauth import build_authorize_url, google_oauth_configured

        assert google_oauth_configured() is True
        authorize_url = build_authorize_url(admin=False, state="test-state")
        assert google_oauth_credentials["client_id"] in authorize_url
        assert "accounts.google.com/o/oauth2/v2/auth" in authorize_url
        assert "state=" in authorize_url


@pytest.mark.email_auth
def test_login_google_redirects_to_google_when_oauth_configured(
    google_oauth_credentials,
):
    app = create_app()
    app.config.update(
        TESTING=True,
        AUTH_MOCK_ENABLED=False,
        GOOGLE_CLIENT_ID=google_oauth_credentials["client_id"],
        GOOGLE_CLIENT_SECRET=google_oauth_credentials["client_secret"],
    )

    response = app.test_client().get("/login/google")

    assert response.status_code == 302
    assert "accounts.google.com/o/oauth2/v2/auth" in response.headers["Location"]
    assert google_oauth_credentials["client_id"] in response.headers["Location"]


def test_build_authorize_url_uses_public_base_url_for_vm():
    app = create_app()
    app.config.update(
        GOOGLE_CLIENT_ID="test-id.apps.googleusercontent.com",
        GOOGLE_CLIENT_SECRET="test-secret",
        PUBLIC_BASE_URL="https://app.example.com",
    )

    with app.app_context():
        from app.c1_ui.google_oauth import build_authorize_url

        user_url = build_authorize_url(admin=False, state="user-state")
        admin_url = build_authorize_url(admin=True, state="admin-state")

    assert (
        "redirect_uri=https%3A%2F%2Fapp.example.com%2Fauth%2Fgoogle%2Fcallback"
        in user_url
    )
    assert (
        "redirect_uri=https%3A%2F%2Fapp.example.com%2Fadmin%2Fauth%2Fgoogle%2Fcallback"
        in admin_url
    )


def test_login_google_falls_back_without_oauth_credentials():
    """OAuth 未設定時は既存のフォールバック URL へリダイレクトする（失敗させない）."""
    app = create_app()
    app.config.update(
        TESTING=True,
        AUTH_MOCK_ENABLED=False,
        GOOGLE_CLIENT_ID="",
        GOOGLE_CLIENT_SECRET="",
        AUTH_GOOGLE_LOGIN_URL="https://auth.example.test/google",
    )

    response = app.test_client().get("/login/google")

    assert response.status_code == 302
    assert response.headers["Location"] == "https://auth.example.test/google"


def test_google_oauth_callback_rejects_invalid_state():
    app = create_app()
    app.config.update(
        TESTING=True,
        AUTH_MOCK_ENABLED=False,
        GOOGLE_CLIENT_ID="test-id.apps.googleusercontent.com",
        GOOGLE_CLIENT_SECRET="test-secret",
    )

    response = app.test_client().get(
        "/auth/google/callback?code=fake-code&state=invalid-state"
    )

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login?")
    assert "state" in response.headers["Location"] or "error=" in response.headers["Location"]


def test_google_oauth_callback_exchanges_code_and_logs_in(monkeypatch):
    app = create_app()
    app.config.update(
        TESTING=True,
        AUTH_MOCK_ENABLED=False,
        AUTH_SERVICE_BASE_URL="http://c2",
        GOOGLE_CLIENT_ID="test-id.apps.googleusercontent.com",
        GOOGLE_CLIENT_SECRET="test-secret",
    )

    class FakeAuthResult:
        auth_token = "oauth-token"
        user_id = "5"

    class FakeAuthServiceClient:
        def login(self, **kwargs):
            assert kwargs["google_auth"]["id_token"] == "google-id-token"
            return FakeAuthResult()

    monkeypatch.setattr("app.c1_ui.routes.AuthServiceClient", FakeAuthServiceClient)

    def fake_exchange(*, code, admin):
        assert code == "auth-code"
        assert admin is False
        return {"id_token": "google-id-token"}

    monkeypatch.setattr("app.c1_ui.routes.exchange_code_for_id_token", fake_exchange)

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["oauth_state_user"] = "valid-state"

        callback_response = client.get(
            "/auth/google/callback?code=auth-code&state=valid-state"
        )
        assert callback_response.status_code == 302
        assert callback_response.headers["Location"].endswith("/auth/callback")

        final_response = client.get("/auth/callback")

    cookies = final_response.headers.getlist("Set-Cookie")
    assert final_response.status_code == 302
    assert final_response.headers["Location"] == "/communities"
    assert any("auth_token=oauth-token" in cookie for cookie in cookies)
    assert any("user_id=5" in cookie for cookie in cookies)
