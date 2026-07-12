import pytest


flask = pytest.importorskip("flask")

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_home_screen_can_be_opened(client, fixture_community_service):
    client.set_cookie("auth_token", "test-token")
    response = client.get("/communities")

    assert response.status_code == 200
    assert "コミュニティ一覧".encode() in response.data


def test_communities_redirects_without_auth_cookie(client):
    response = client.get("/communities", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert "error=" in response.headers["Location"]


def test_login_screen_shows_email_form_in_mock_mode(client):
    client.application.config["AUTH_MOCK_ENABLED"] = True
    response = client.get("/login")

    assert response.status_code == 200
    assert b'type="email"' in response.data
    assert "メールアドレスでログイン".encode() in response.data


def test_login_screen_shows_google_button_in_oauth_mode(monkeypatch):
    monkeypatch.setenv("AUTH_MOCK_ENABLED", "0")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")

    app = create_app()
    response = app.test_client().get("/login")

    assert response.status_code == 200
    assert b'type="email"' not in response.data
    assert "大学Googleアカウントでログイン".encode() in response.data


def test_email_login_rejects_non_university_domain(client):
    client.application.config["AUTH_MOCK_ENABLED"] = True
    response = client.post(
        "/login/email",
        data={"email": "student@gmail.com"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "error=" in response.headers["Location"]
    assert "shibaura-it.ac.jp".encode() in response.headers["Location"].encode()


def test_login_screen_does_not_have_password_input(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert b'type="password"' not in response.data


def test_theme_stylesheet_can_be_selected(client):
    response = client.get("/login?theme=campus")

    assert response.status_code == 200
    assert b"theme-campus.css" in response.data
    assert b'theme-campus' in response.data


def test_selected_theme_is_kept_in_search_form(client, fixture_community_service):
    client.set_cookie("auth_token", "test-token")
    response = client.get("/communities?theme=compact")

    assert response.status_code == 200
    assert b'name="theme" value="compact"' in response.data


def test_unknown_theme_falls_back_to_classic(client):
    response = client.get("/login?theme=unknown")

    assert response.status_code == 200
    assert b"theme-campus.css" not in response.data
    assert b'theme-classic' in response.data


def test_mock_user_login_redirects_to_login_form(client):
    client.application.config["AUTH_MOCK_ENABLED"] = True
    response = client.get("/login/google")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_mock_admin_login_redirects_to_admin_login_form(client):
    client.application.config["AUTH_MOCK_ENABLED"] = True
    response = client.get("/admin/login/google")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/login")


def test_auth_callback_rejects_direct_token_without_backend(client):
    response = client.get("/auth/callback?auth_token=demo-token")

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login?")
    assert "error=" in response.headers["Location"]


def test_email_login_stores_issued_token(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, AUTH_SERVICE_BASE_URL="http://c2")

    class FakeAuthResult:
        auth_token = "issued-token"
        user_id = "1"

    class FakeAuthServiceClient:
        def login(self, **kwargs):
            return FakeAuthResult()

        def verify_token(self, auth_token):
            return FakeAuthResult()

    monkeypatch.setattr("app.c1_ui.routes.AuthServiceClient", FakeAuthServiceClient)

    response = app.test_client().post(
        "/login/email",
        data={"email": "student@shibaura-it.ac.jp"},
    )

    cookies = response.headers.getlist("Set-Cookie")
    assert response.status_code == 302
    assert response.headers["Location"] == "/communities"
    assert any("auth_token=issued-token" in cookie for cookie in cookies)
    assert any("user_id=1" in cookie for cookie in cookies)


def test_mock_auth_callback_stores_user_id(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, AUTH_SERVICE_BASE_URL="http://c2")

    class FakeAuthResult:
        auth_token = "issued-token"
        user_id = "1"

    class FakeAuthServiceClient:
        def login(self, **kwargs):
            return FakeAuthResult()

    monkeypatch.setattr("app.c1_ui.routes.AuthServiceClient", FakeAuthServiceClient)

    response = app.test_client().get(
        "/auth/callback?id_token=dummy-id-token"
    )

    cookies = response.headers.getlist("Set-Cookie")
    assert response.status_code == 302
    assert any("auth_token=issued-token" in cookie for cookie in cookies)
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
            "/auth/callback?id_token=dummy-id-token"
        )

    cookies = response.headers.getlist("Set-Cookie")
    assert response.status_code == 302
    assert captured["google_auth"]["id_token"] == "dummy-id-token"
    assert captured["fallback_auth_token"] is None
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
            "/admin/auth/callback?id_token=dummy-admin-id-token"
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


def test_create_form_has_live_image_preview_hooks(client):
    client.set_cookie("auth_token", "test-token")
    response = client.get("/communities/new")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "data-community-form" in body
    assert "data-image-input" in body
    assert 'src="data:image/svg+xml;charset=UTF-8' in body
    assert body.count('data-placeholder-src="data:image/svg+xml;charset=UTF-8') == 1


def test_edit_form_keeps_existing_image_reference(monkeypatch, client):
    class FakeCommunityServiceClient:
        def get_community_detail(self, **kwargs):
            return type(
                "CommunityDetail",
                (),
                {
                    "community_id": "web-design",
                    "name": "Web制作研究会",
                    "category": "制作",
                    "summary": "概要",
                    "content": "本文",
                    "contact": "",
                    "image_url": "/api-proxy/uploads/web.png",
                    "can_edit": True,
                    "can_delete": True,
                },
            )()

    monkeypatch.setattr("app.c1_ui.routes.CommunityServiceClient", FakeCommunityServiceClient)
    client.set_cookie("auth_token", "test-token")

    response = client.get("/communities/web-design/edit")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'src="/api-proxy/uploads/web.png"' in body
    assert 'data-placeholder-src="data:image/svg+xml;charset=UTF-8' in body


def test_detail_screen_can_be_opened(client, fixture_community_service):
    client.set_cookie("auth_token", "test-token")
    response = client.get("/communities/web-design")

    assert response.status_code == 200
    assert "Web制作研究会".encode() in response.data
