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
    assert "コミュニティ一覧".encode() in response.data


def test_login_screen_does_not_have_password_input(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert b'input type="password"' not in response.data


def test_theme_stylesheet_can_be_selected(client):
    response = client.get("/login?theme=campus")

    assert response.status_code == 200
    assert b"theme-campus.css" in response.data
    assert b'theme-campus' in response.data


def test_selected_theme_is_kept_in_search_form(client):
    client.set_cookie("auth_token", "test-token")
    response = client.get("/communities?theme=compact")

    assert response.status_code == 200
    assert b'name="theme" value="compact"' in response.data


def test_unknown_theme_falls_back_to_classic(client):
    response = client.get("/login?theme=unknown")

    assert response.status_code == 200
    assert b"theme-campus.css" not in response.data
    assert b'theme-classic' in response.data


def test_mock_user_login_redirects_to_callback(client):
    response = client.get("/login/google")

    assert response.status_code == 302
    assert "/auth/callback" in response.headers["Location"]
    assert "auth_token=mock-user-token" in response.headers["Location"]
    assert "user_id=1" in response.headers["Location"]


def test_mock_admin_login_redirects_to_admin_callback(client):
    response = client.get("/admin/login/google")

    assert response.status_code == 302
    assert "/admin/auth/callback" in response.headers["Location"]
    assert "auth_token=mock-admin-token" in response.headers["Location"]
    assert "user_id=2" in response.headers["Location"]


def test_auth_callback_stores_demo_token_without_auth_service(client):
    response = client.get("/auth/callback?auth_token=demo-token")

    assert response.status_code == 302
    assert response.headers["Location"] == "/communities"
    assert "auth_token=demo-token" in response.headers.get("Set-Cookie", "")


def test_mock_auth_callback_stores_user_id(client):
    response = client.get("/auth/callback?auth_token=mock-user-token&user_id=1")

    cookies = response.headers.getlist("Set-Cookie")
    assert response.status_code == 302
    assert any("auth_token=mock-user-token" in cookie for cookie in cookies)
    assert any("user_id=1" in cookie for cookie in cookies)


def test_auth_callback_uses_auth_service_user_id(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, AUTH_SERVICE_BASE_URL="http://c2")
    captured = {}

    class FakeAuthResult:
        auth_token = "token-1"
        user_id = "3"

    class FakeAuthServiceClient:
        def login(self, **kwargs):
            captured.update(kwargs)
            return FakeAuthResult()

    monkeypatch.setattr("app.c1_ui.routes.AuthServiceClient", FakeAuthServiceClient)

    with app.test_client() as test_client:
        response = test_client.get(
            "/auth/callback?email=student@shibaura-it.ac.jp&auth_token=token-1"
        )

    cookies = response.headers.getlist("Set-Cookie")
    assert response.status_code == 302
    assert captured["google_auth"]["email"] == "student@shibaura-it.ac.jp"
    assert captured["fallback_auth_token"] == "token-1"
    assert captured["admin"] is False
    assert any("auth_token=token-1" in cookie for cookie in cookies)
    assert any("user_id=3" in cookie for cookie in cookies)


def test_admin_auth_callback_uses_admin_mode(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, AUTH_SERVICE_BASE_URL="http://c2")
    captured = {}

    class FakeAuthResult:
        auth_token = "admin-token"
        user_id = "4"

    class FakeAuthServiceClient:
        def login(self, **kwargs):
            captured.update(kwargs)
            return FakeAuthResult()

    monkeypatch.setattr("app.c1_ui.routes.AuthServiceClient", FakeAuthServiceClient)

    with app.test_client() as test_client:
        response = test_client.get(
            "/admin/auth/callback?email=admin@shibaura-it.ac.jp&auth_token=admin-token"
        )

    assert response.status_code == 302
    assert captured["admin"] is True


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
