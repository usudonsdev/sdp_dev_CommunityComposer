import pytest


flask = pytest.importorskip("flask")

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_home_screen_can_be_opened(client):
    client.set_cookie("auth_token", "test-token")
    response = client.get("/communities")

    assert response.status_code == 200
    assert "Find a place".encode() in response.data


def test_login_screen_does_not_have_password_input(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert b'input type="password"' not in response.data


def test_create_form_validates_required_fields(client):
    client.set_cookie("auth_token", "test-token")
    response = client.post(
        "/communities",
        data={
            "name": "",
            "category": "制作",
            "summary": "概要",
            "content": "",
            "contact": "sit-web@example.com",
        },
    )

    assert response.status_code == 400


def test_create_form_can_be_opened(client):
    client.set_cookie("auth_token", "test-token")
    response = client.get("/communities/new")

    assert response.status_code == 200
    assert "コミュニティ名".encode() in response.data


def test_detail_screen_can_be_opened(client):
    client.set_cookie("auth_token", "test-token")
    response = client.get("/communities/web-design")

    assert response.status_code == 200
    assert "Web制作研究会".encode() in response.data
