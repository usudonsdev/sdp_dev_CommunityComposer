# -*- coding: utf-8 -*-
from app import create_app


def test_mock_email_login_registers_user_and_issues_token():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        from app.extensions import db

        db.create_all()

    with app.test_client() as client:
        response = client.post(
            "/auth/login",
            json={
                "mock_email_auth": "1",
                "email": "student@shibaura-it.ac.jp",
            },
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["email"] == "student@shibaura-it.ac.jp"
    assert body["auth_token"]
    assert body["user"]["email"] == "student@shibaura-it.ac.jp"


def test_admin_email_login_via_mock_auth():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        from app.extensions import db

        db.create_all()

    with app.test_client() as client:
        response = client.post(
            "/admin/auth/login",
            json={
                "mock_email_auth": "1",
                "email": "adminAL24000@shibaura-it.ac.jp",
            },
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["user"]["role"] == "admin"
    assert body["email"] == "adminal24000@shibaura-it.ac.jp"


def test_mock_email_login_rejects_invalid_domain():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.test_client() as client:
        response = client.post(
            "/auth/login",
            json={
                "mock_email_auth": "1",
                "email": "student@gmail.com",
            },
        )

    assert response.status_code == 400
    assert "shibaura-it.ac.jp" in response.get_json()["error"]


def test_auth_verify_accepts_issued_token():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        from app.extensions import db

        db.create_all()

    with app.test_client() as client:
        login_response = client.post(
            "/auth/login",
            json={
                "mock_email_auth": "1",
                "email": "member@shibaura-it.ac.jp",
            },
        )
        token = login_response.get_json()["auth_token"]

        verify_response = client.get(f"/auth/verify?auth_token={token}")

    assert verify_response.status_code == 200
    body = verify_response.get_json()
    assert body["email"] == "member@shibaura-it.ac.jp"
    assert body["role"] == "user"


def test_auth_verify_rejects_invalid_token():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        from app.extensions import db

        db.create_all()

    with app.test_client() as client:
        response = client.get("/auth/verify?auth_token=invalid-token")

    assert response.status_code == 401
