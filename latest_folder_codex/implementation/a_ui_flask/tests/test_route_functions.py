from urllib.parse import parse_qs, urlparse

import pytest

from app import create_app
from app.c1_ui import routes
from app.c1_ui.models import CommunityDetail
from app.c1_ui.service_clients import (
    AuthServiceRejected,
    CommunityServiceRejected,
    CommunityServiceUnavailable,
)


@pytest.fixture()
def app():
    test_app = create_app()
    test_app.config.update(TESTING=True)
    return test_app


@pytest.fixture()
def client(app):
    return app.test_client()


def test_create_app_registers_c1_ui_blueprint():
    test_app = create_app()

    assert "c1_ui" in test_app.blueprints


def test_auth_token_reads_configured_cookie(app):
    with app.test_request_context("/communities", headers={"Cookie": "auth_token=test-token"}):
        assert routes.auth_token() == "test-token"


def test_current_user_id_prefers_cookie_over_config(app):
    app.config["COMMUNITY_CREATOR_USER_ID"] = "7"

    with app.test_request_context("/communities", headers={"Cookie": "user_id=42"}):
        assert routes.current_user_id() == "42"


def test_current_user_id_falls_back_to_config(app):
    app.config["COMMUNITY_CREATOR_USER_ID"] = "7"

    with app.test_request_context("/communities"):
        assert routes.current_user_id() == "7"


def test_mock_auth_enabled_returns_boolean_from_config(app):
    app.config["AUTH_MOCK_ENABLED"] = ""

    with app.test_request_context("/login"):
        assert routes.mock_auth_enabled() is False


def test_mock_auth_enabled_treats_string_zero_as_disabled(app):
    app.config["AUTH_MOCK_ENABLED"] = "0"

    with app.test_request_context("/login"):
        assert routes.mock_auth_enabled() is False


def test_apply_env_config_parses_auth_mock_enabled_zero(monkeypatch):
    monkeypatch.setenv("AUTH_MOCK_ENABLED", "0")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")

    app = create_app()

    assert app.config["AUTH_MOCK_ENABLED"] is False


def test_apply_env_config_disables_mock_when_oauth_credentials_present(monkeypatch):
    monkeypatch.delenv("AUTH_MOCK_ENABLED", raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")

    app = create_app()

    assert app.config["AUTH_MOCK_ENABLED"] is False


def test_require_auth_redirects_to_login_when_cookie_is_missing(app):
    with app.test_request_context("/communities"):
        response = routes.require_auth()

    assert response.status_code == 302
    assert "/login?" in response.headers["Location"]
    assert "error=" in response.headers["Location"]


def test_require_auth_allows_request_when_auth_is_disabled(app):
    app.config["REQUIRE_AUTH_TOKEN"] = False

    with app.test_request_context("/communities"):
        assert routes.require_auth() is None


def test_require_auth_rejects_mock_token_when_mock_disabled(app):
    app.config["AUTH_MOCK_ENABLED"] = False

    with app.test_request_context(
        "/communities",
        headers={"Cookie": "auth_token=mock-user-token"},
    ):
        response = routes.require_auth()

    assert response.status_code == 302
    assert "/login?" in response.headers["Location"]
    assert response.headers.getlist("Set-Cookie")


def test_show_login_ignores_mock_token_when_mock_disabled(client):
    client.set_cookie("auth_token", "mock-user-token")
    app = client.application
    app.config["AUTH_MOCK_ENABLED"] = False

    response = client.get("/login")

    assert response.status_code == 200
    assert "大学Googleアカウントでログイン".encode() in response.data


def test_template_context_keeps_known_theme_and_categories(app):
    with app.test_request_context("/communities?theme=social", headers={"Cookie": "auth_token=t"}):
        context = routes.template_context(title="テスト")

    assert context["title"] == "テスト"
    assert context["auth_token"] == "t"
    assert context["selected_theme"] == "social"
    assert context["theme_stylesheet"] == "theme-social.css"
    assert context["categories"] == ["スポーツ", "制作", "学習", "その他"]


def test_template_context_falls_back_unknown_theme_to_classic(app):
    with app.test_request_context("/communities?theme=unknown"):
        context = routes.template_context()

    assert context["selected_theme"] == "classic"
    assert context["theme_stylesheet"] is None


def test_mock_auth_params_returns_user_and_admin_values(app):
    with app.test_request_context("/login"):
        user_params = routes.mock_auth_params(admin=False)
        admin_params = routes.mock_auth_params(admin=True)

    assert user_params == {
        "email": "student@shibaura-it.ac.jp",
        "mock_email_auth": "1",
        "user_id": "1",
    }
    assert admin_params == {
        "email": "admin@shibaura-it.ac.jp",
        "mock_email_auth": "1",
        "user_id": "2",
    }


def test_form_data_from_request_maps_expected_fields(app):
    with app.test_request_context(
        "/communities",
        method="POST",
        data={
            "name": "Web制作研究会",
            "category": "制作",
            "summary": "UI設計を学ぶ",
            "content": "連絡先も本文に書く",
            "contact": "ignored@example.com",
            "image_url": "",
        },
    ):
        form = routes.form_data_from_request()

    assert form.name == "Web制作研究会"
    assert form.category == "制作"
    assert form.summary == "UI設計を学ぶ"
    assert form.content == "連絡先も本文に書く"
    assert form.contact == ""
    assert form.image_url is None


def test_root_redirects_to_login_when_unauthenticated(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login?")


def test_login_redirects_to_home_when_already_authenticated(client):
    client.set_cookie("auth_token", "test-token")

    response = client.get("/login")

    assert response.status_code == 302
    assert response.headers["Location"] == "/communities"


def test_login_force_clears_existing_auth_cookie(client):
    client.set_cookie("auth_token", "test-token")
    client.set_cookie("user_id", "7")

    response = client.get("/login?force=1")

    cookies = response.headers.getlist("Set-Cookie")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
    assert any("auth_token=;" in cookie for cookie in cookies)
    assert any("user_id=;" in cookie for cookie in cookies)


def test_logout_clears_auth_cookies(client):
    client.set_cookie("auth_token", "test-token")
    client.set_cookie("user_id", "7")

    response = client.get("/logout")

    cookies = response.headers.getlist("Set-Cookie")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login?")
    assert any("auth_token=;" in cookie for cookie in cookies)
    assert any("user_id=;" in cookie for cookie in cookies)


def test_request_login_uses_configured_google_url_when_mock_disabled():
    test_app = create_app()
    test_app.config.update(
        TESTING=True,
        AUTH_MOCK_ENABLED=False,
        GOOGLE_CLIENT_ID="",
        GOOGLE_CLIENT_SECRET="",
        AUTH_GOOGLE_LOGIN_URL="https://auth.example.test/google",
    )

    response = test_app.test_client().get("/login/google")

    assert response.status_code == 302
    assert response.headers["Location"] == "https://auth.example.test/google"


def test_request_admin_login_uses_configured_google_url_when_mock_disabled():
    test_app = create_app()
    test_app.config.update(
        TESTING=True,
        AUTH_MOCK_ENABLED=False,
        GOOGLE_CLIENT_ID="",
        GOOGLE_CLIENT_SECRET="",
        AUTH_ADMIN_GOOGLE_LOGIN_URL="https://auth.example.test/admin-google",
    )

    response = test_app.test_client().get("/admin/login/google")

    assert response.status_code == 302
    assert response.headers["Location"] == "https://auth.example.test/admin-google"


def test_auth_callback_error_redirects_back_to_login(client):
    response = client.get("/auth/callback?error=denied")
    query = parse_qs(urlparse(response.headers["Location"]).query)

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login?")
    assert query["error"] == ["denied"]


def test_auth_callback_redirects_with_service_error(monkeypatch, client):
    class FailingAuthServiceClient:
        def login(self, **kwargs):
            raise AuthServiceRejected("認証できません。", status_code=401)

    monkeypatch.setattr(routes, "AuthServiceClient", FailingAuthServiceClient)

    response = client.get("/auth/callback?id_token=bad-token")
    query = parse_qs(urlparse(response.headers["Location"]).query)

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login?")
    assert query["error"] == ["認証できません。"]


def test_home_returns_503_when_community_service_is_unavailable(monkeypatch, client):
    class FailingCommunityServiceClient:
        def get_community_list(self, **kwargs):
            raise CommunityServiceUnavailable("一覧取得に失敗")

    monkeypatch.setattr(routes, "CommunityServiceClient", FailingCommunityServiceClient)
    client.set_cookie("auth_token", "test-token")

    response = client.get("/communities")

    assert response.status_code == 503
    assert "一覧取得に失敗".encode() in response.data


def test_save_community_redirects_to_saved_detail(monkeypatch, client):
    captured = {}

    class SavingCommunityServiceClient:
        def save_community(self, **kwargs):
            captured.update(kwargs)
            return "new-community"

    monkeypatch.setattr(routes, "CommunityServiceClient", SavingCommunityServiceClient)
    client.set_cookie("auth_token", "test-token")
    client.set_cookie("user_id", "9")

    response = client.post(
        "/communities",
        data={
            "name": "Web制作研究会",
            "category": "制作",
            "summary": "概要",
            "content": "本文",
            "image_url": "https://example.test/image.png",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/communities/new-community"
    assert captured["auth_token"] == "test-token"
    assert captured["creator_user_id"] == "9"
    assert captured["data"].image_url == "https://example.test/image.png"


def test_save_community_returns_service_error_status(monkeypatch, client):
    class RejectingCommunityServiceClient:
        def save_community(self, **kwargs):
            raise CommunityServiceRejected("登録できません。", status_code=409)

    monkeypatch.setattr(routes, "CommunityServiceClient", RejectingCommunityServiceClient)
    client.set_cookie("auth_token", "test-token")

    response = client.post(
        "/communities",
        data={
            "name": "Web制作研究会",
            "category": "制作",
            "summary": "概要",
            "content": "本文",
        },
    )

    assert response.status_code == 409
    assert "登録できません。".encode() in response.data


def test_detail_returns_404_when_community_is_missing(client, fixture_community_service):
    client.set_cookie("auth_token", "test-token")

    response = client.get("/communities/missing")

    assert response.status_code == 404
    assert "対象コミュニティが存在しない".encode() in response.data


def test_edit_form_can_be_opened(client, fixture_community_service):
    client.set_cookie("auth_token", "test-token")

    response = client.get("/communities/web-design/edit")

    assert response.status_code == 200
    assert "Web制作研究会".encode() in response.data
    assert "コミュニティ内容".encode() in response.data


def test_edit_form_returns_503_when_detail_service_fails(monkeypatch, client):
    class FailingCommunityServiceClient:
        def get_community_detail(self, **kwargs):
            raise CommunityServiceUnavailable("詳細取得に失敗")

    monkeypatch.setattr(routes, "CommunityServiceClient", FailingCommunityServiceClient)
    client.set_cookie("auth_token", "test-token")

    response = client.get("/communities/web-design/edit")

    assert response.status_code == 503
    assert "詳細取得に失敗".encode() in response.data


def test_update_community_redirects_to_saved_detail(monkeypatch, client):
    captured = {}

    class SavingCommunityServiceClient:
        def save_community(self, **kwargs):
            captured.update(kwargs)
            return "web-design"

    monkeypatch.setattr(routes, "CommunityServiceClient", SavingCommunityServiceClient)
    client.set_cookie("auth_token", "test-token")

    response = client.post(
        "/communities/web-design",
        data={
            "name": "Web制作研究会",
            "category": "制作",
            "summary": "概要",
            "content": "本文",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/communities/web-design"
    assert captured["community_id"] == "web-design"
    assert "creator_user_id" not in captured


def test_update_community_validates_form_before_service_call(monkeypatch, client):
    class UnexpectedCommunityServiceClient:
        def save_community(self, **kwargs):
            raise AssertionError("validation should stop before service call")

    monkeypatch.setattr(routes, "CommunityServiceClient", UnexpectedCommunityServiceClient)
    client.set_cookie("auth_token", "test-token")

    response = client.post(
        "/communities/web-design",
        data={"name": "", "category": "制作", "summary": "概要", "content": ""},
    )

    assert response.status_code == 400


def test_delete_community_redirects_to_home(monkeypatch, client):
    captured = {}

    class DeletingCommunityServiceClient:
        def delete_community(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(routes, "CommunityServiceClient", DeletingCommunityServiceClient)
    client.set_cookie("auth_token", "test-token")

    response = client.post("/communities/web-design/delete")

    assert response.status_code == 302
    assert response.headers["Location"] == "/communities"
    assert captured == {"community_id": "web-design", "auth_token": "test-token"}


def test_delete_community_returns_service_error_status(monkeypatch, client):
    class RejectingCommunityServiceClient:
        def delete_community(self, **kwargs):
            raise CommunityServiceRejected("削除できません。", status_code=403)

    monkeypatch.setattr(routes, "CommunityServiceClient", RejectingCommunityServiceClient)
    client.set_cookie("auth_token", "test-token")

    response = client.post("/communities/web-design/delete")

    assert response.status_code == 403
    assert "削除できません。".encode() in response.data


def test_not_implemented_returns_501(client):
    response = client.get("/not-implemented/c2/google-login")

    assert response.status_code == 501
    assert "外部処理部が未接続".encode() in response.data
