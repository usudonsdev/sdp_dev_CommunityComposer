# -*- coding: utf-8 -*-
from unittest.mock import patch

import pytest

from app import create_app
from tests.conftest import is_google_oauth_configured


def test_auth_login_accepts_id_token_with_mocked_google():
    """Google OAuth 設定が無くても、モックで id_token ログイン経路を検証する."""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "ADMIN_LOGIN_SECRET": "admin-secret",
            "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        }
    )

    with app.app_context():
        from app.extensions import db
        from app.models.user import User

        user = User(email="student@shibaura-it.ac.jp", role="user")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with patch("app.routes.users.AuthService") as mock_auth_service_cls:
        mock_service = mock_auth_service_cls.return_value
        mock_service.verify_google_account.return_value = {
            "status": "OK",
            "user_id": user_id,
            "email": "student@shibaura-it.ac.jp",
        }
        mock_service.issue_login_token.return_value = {
            "status": "OK",
            "auth_token": "issued-token",
            "expires_at": "2026-06-17 12:00:00",
        }

        with app.test_client() as client:
            response = client.post(
                "/auth/login",
                json={"id_token": "dummy-id-token"},
            )

    assert response.status_code == 200
    body = response.get_json()
    assert body["auth_token"] == "issued-token"
    assert body["email"] == "student@shibaura-it.ac.jp"


def test_admin_auth_login_rejects_non_admin_with_mocked_google():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "ADMIN_LOGIN_SECRET": "admin-secret",
            "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        }
    )

    with app.test_client() as client:
        client.post(
            "/auth/login",
            json={
                "email": "member@shibaura-it.ac.jp",
                "auth_token": "member-token",
            },
        )

    with patch("app.routes.users.AuthService") as mock_auth_service_cls:
        mock_service = mock_auth_service_cls.return_value
        mock_service.verify_google_account.return_value = {
            "status": "OK",
            "user_id": 1,
            "email": "member@shibaura-it.ac.jp",
        }
        mock_service.verify_admin_role.return_value = {
            "status": "NG",
            "reason": "管理者権限がありません",
            "role": "user",
        }

        with app.test_client() as client:
            response = client.post(
                "/admin/auth/login",
                json={"id_token": "dummy-admin-id-token"},
            )

    assert response.status_code == 403
    assert response.get_json()["error"] == "管理者権限がありません"


@pytest.mark.email_auth
def test_google_oauth_env_is_available_for_live_email_auth(google_oauth_credentials):
    """ローカルに OAuth クライアント情報がある場合のみ実行する任意テスト."""
    assert is_google_oauth_configured()
    assert google_oauth_credentials["client_id"].endswith(".apps.googleusercontent.com")
    assert google_oauth_credentials["client_secret"]


def test_verify_google_account_rejects_unverified_email():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
        }
    )

    with patch("app.services.auth_service.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = {
            "email": "student@shibaura-it.ac.jp",
            "email_verified": False,
        }

        with app.app_context():
            from app.services.auth_service import AuthService

            result = AuthService().verify_google_account({"id_token": "token"})

    assert result["status"] == "NG"
    assert "確認済み" in result["reason"]
