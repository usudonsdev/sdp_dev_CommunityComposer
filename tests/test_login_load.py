from datetime import datetime

from app import create_app
from app.services.auth_service import AuthService, _VERIFY_CACHE, _VERIFY_CACHE_LOCK


def _app():
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "AUTH_VERIFY_CACHE_TTL_SECONDS": 30,
        }
    )


def test_verify_login_token_uses_in_memory_cache():
    app = _app()
    auth_service = AuthService()

    with app.app_context():
        with app.test_client() as client:
            login_response = client.post(
                "/auth/login",
                json={
                    "email": "cache@shibaura-it.ac.jp",
                    "mock_email_auth": "1",
                },
            )
            auth_token = login_response.get_json()["auth_token"]

        with _VERIFY_CACHE_LOCK:
            _VERIFY_CACHE.clear()

        now = datetime.utcnow()
        first = auth_service.verify_login_token(auth_token=auth_token, c_time=now)
        with _VERIFY_CACHE_LOCK:
            assert auth_token in _VERIFY_CACHE

        second = auth_service.verify_login_token(auth_token=auth_token, c_time=now)
        assert first == second
        assert first["status"] == "OK"


def test_password_login_runs_via_login_executor():
    app = _app()

    with app.test_client() as client:
        client.post(
            "/auth/register",
            json={
                "email": "executor@shibaura-it.ac.jp",
                "password": "secret123",
            },
        )
        response = client.post(
            "/auth/login",
            json={
                "email": "executor@shibaura-it.ac.jp",
                "password": "secret123",
            },
        )

    assert response.status_code == 200
    assert response.get_json()["auth_token"]
