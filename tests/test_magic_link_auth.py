# -*- coding: utf-8 -*-
from app import create_app


def _app():
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SMTP_HOST": "smtp.test.local",
            "SMTP_FROM": "noreply@test.local",
            "MAGIC_LINK_CAPTURE_OUTBOX": True,
            "MAGIC_LINK_OUTBOX": [],
        }
    )


def test_magic_link_request_sends_email_and_verify_issues_token():
    app = _app()

    with app.app_context():
        from app.extensions import db

        db.create_all()

    with app.test_client() as client:
        request_response = client.post(
            "/auth/magic-link",
            json={
                "email": "student@shibaura-it.ac.jp",
                "verify_base_url": "http://localhost:8080",
            },
        )

        assert request_response.status_code == 200
        outbox = app.config["MAGIC_LINK_OUTBOX"]
        assert len(outbox) == 1
        assert outbox[0]["to"] == "student@shibaura-it.ac.jp"
        assert "token=" in outbox[0]["verify_url"]

        token = outbox[0]["verify_url"].split("token=", 1)[1]
        verify_response = client.get(f"/auth/magic-link/verify?token={token}")

    assert verify_response.status_code == 200
    body = verify_response.get_json()
    assert body["auth_token"]
    assert body["email"] == "student@shibaura-it.ac.jp"


def test_magic_link_rejects_invalid_domain():
    app = _app()

    with app.test_client() as client:
        response = client.post(
            "/auth/magic-link",
            json={
                "email": "student@gmail.com",
                "verify_base_url": "http://localhost:8080",
            },
        )

    assert response.status_code == 400
    assert "shibaura-it.ac.jp" in response.get_json()["error"]


def test_magic_link_token_is_one_time_use():
    app = _app()

    with app.app_context():
        from app.extensions import db

        db.create_all()

    with app.test_client() as client:
        client.post(
            "/auth/magic-link",
            json={
                "email": "member@shibaura-it.ac.jp",
                "verify_base_url": "http://localhost:8080",
            },
        )
        token = app.config["MAGIC_LINK_OUTBOX"][0]["verify_url"].split("token=", 1)[1]

        first = client.get(f"/auth/magic-link/verify?token={token}")
        second = client.get(f"/auth/magic-link/verify?token={token}")

    assert first.status_code == 200
    assert second.status_code == 400
    assert "既に使用" in second.get_json()["error"]


def test_magic_link_requires_smtp_configuration():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SMTP_HOST": "",
            "SMTP_FROM": "",
        }
    )

    with app.test_client() as client:
        response = client.post(
            "/auth/magic-link",
            json={
                "email": "student@shibaura-it.ac.jp",
                "verify_base_url": "http://localhost:8080",
            },
        )

    assert response.status_code == 503
