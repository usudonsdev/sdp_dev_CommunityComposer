import pytest

from app import create_app
from app.c1_ui.models import CommunityFormData
from app.c1_ui.service_clients import (
    AuthServiceClient,
    CommunityServiceClient,
    CommunityServiceRejected,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("request failed")


def test_get_community_list_accepts_db_repository_response(monkeypatch):
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return FakeResponse(
            {
                "communities": [
                    {
                        "id": 12,
                        "name": "Web制作研究会",
                        "category": "制作",
                        "summary": "UI設計を学ぶ",
                        "content": "週に1回活動する",
                        "image_path": "/uploads/web.png",
                        "created_at": "2026-06-01T12:00:00",
                        "updated_at": "2026-06-08T12:00:00",
                        "can_edit": True,
                        "can_delete": True,
                    }
                ]
            }
        )

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    communities = CommunityServiceClient(base_url="http://c3").get_community_list(
        keyword="Web",
        category="制作",
        auth_token="token-1",
    )

    assert captured["method"] == "get"
    assert captured["url"] == "http://c3/communities"
    assert captured["kwargs"]["params"]["q"] == "Web"
    assert captured["kwargs"]["params"]["category"] == "制作"
    assert captured["kwargs"]["params"]["auth_token"] == "token-1"
    assert communities[0].community_id == "12"
    assert communities[0].image_url == "http://c3/uploads/web.png"
    assert communities[0].can_edit is True


def test_save_community_sends_db_repository_payload(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, COMMUNITY_CREATOR_USER_ID="7")
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return FakeResponse(
            {
                "community": {
                    "id": 13,
                    "name": "Web制作研究会",
                    "category": "制作",
                    "summary": "UI設計を学ぶ",
                    "content": "週に1回活動する",
                    "image_path": "/uploads/web.png",
                    "created_at": "2026-06-01T12:00:00",
                    "updated_at": "2026-06-08T12:00:00",
                }
            },
            status_code=201,
        )

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    with app.app_context():
        community_id = CommunityServiceClient(base_url="http://c3").save_community(
            data=CommunityFormData(
                name="Web制作研究会",
                category="制作",
                summary="UI設計を学ぶ",
                content="週に1回活動する",
                contact="sit-web@example.com",
                image_url="/uploads/web.png",
            ),
            auth_token="token-1",
        )

    payload = captured["kwargs"]["json"]
    assert community_id == "13"
    assert captured["method"] == "post"
    assert payload["creator_user_id"] == 7
    assert payload["auth_token"] == "token-1"
    assert "contact" not in payload
    assert payload["image_path"] == "/uploads/web.png"


def test_save_community_uses_authenticated_user_id(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, COMMUNITY_CREATOR_USER_ID="")
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return FakeResponse(
            {
                "community": {
                    "id": 14,
                    "name": "Web制作研究会",
                    "category": "制作",
                    "summary": "UI設計を学ぶ",
                    "content": "週に1回活動する",
                    "created_at": "2026-06-01T12:00:00",
                    "updated_at": "2026-06-08T12:00:00",
                }
            },
            status_code=201,
        )

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    with app.app_context():
        CommunityServiceClient(base_url="http://c3").save_community(
            data=CommunityFormData(
                name="Web制作研究会",
                category="制作",
                summary="UI設計を学ぶ",
                content="週に1回活動する",
                contact="sit-web@example.com",
            ),
            auth_token="token-1",
            creator_user_id="21",
        )

    assert captured["kwargs"]["json"]["creator_user_id"] == 21


def test_update_community_does_not_send_creator_user_id(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, COMMUNITY_CREATOR_USER_ID="7")
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return FakeResponse(
            {
                "community": {
                    "id": 14,
                    "name": "Web制作研究会",
                    "category": "制作",
                    "summary": "UI設計を学ぶ",
                    "content": "週に1回活動する",
                    "created_at": "2026-06-01T12:00:00",
                    "updated_at": "2026-06-08T12:00:00",
                }
            }
        )

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    with app.app_context():
        CommunityServiceClient(base_url="http://c3").save_community(
            data=CommunityFormData(
                name="Web制作研究会",
                category="制作",
                summary="UI設計を学ぶ",
                content="週に1回活動する",
                contact="sit-web@example.com",
            ),
            auth_token="token-1",
            creator_user_id="21",
            community_id="14",
        )

    payload = captured["kwargs"]["json"]
    assert captured["method"] == "put"
    assert "creator_user_id" not in payload
    assert payload["auth_token"] == "token-1"


def test_service_rejected_keeps_status_code(monkeypatch):
    def fake_request(method, url, **kwargs):
        return FakeResponse({"error": "permission denied"}, status_code=403)

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    with pytest.raises(CommunityServiceRejected) as exc_info:
        CommunityServiceClient(base_url="http://c3").delete_community(
            community_id="13",
            auth_token="token-1",
        )

    assert exc_info.value.status_code == 403
    assert "permission denied" in str(exc_info.value)


def test_auth_service_login_accepts_auth_repository_response(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return FakeResponse(
            {
                "user": {
                    "id": 3,
                    "email": "student@shibaura-it.ac.jp",
                    "role": "user",
                }
            }
        )

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    with app.app_context():
        result = AuthServiceClient(base_url="http://c2").login(
            google_auth={"email": "student@shibaura-it.ac.jp"},
            fallback_auth_token="token-1",
        )

    assert captured["method"] == "post"
    assert captured["url"] == "http://c2/auth/login"
    assert captured["kwargs"]["json"]["email"] == "student@shibaura-it.ac.jp"
    assert captured["kwargs"]["json"]["auth_token"] == "token-1"
    assert result.auth_token == "token-1"
    assert result.user_id == "3"
    assert result.email == "student@shibaura-it.ac.jp"


def test_auth_service_mock_result_keeps_user_id_without_auth_repository():
    app = create_app()
    app.config.update(TESTING=True, AUTH_SERVICE_BASE_URL="")

    with app.app_context():
        result = AuthServiceClient().login(
            google_auth={
                "email": "student@shibaura-it.ac.jp",
                "user_id": "1",
            },
            fallback_auth_token="local-token",
        )

    assert result.auth_token == "local-token"
    assert result.user_id == "1"
    assert result.email == "student@shibaura-it.ac.jp"
    assert result.role == "user"


def test_auth_service_uses_community_service_for_mock_login(monkeypatch):
    app = create_app()
    app.config.update(
        TESTING=True,
        AUTH_SERVICE_BASE_URL="",
        COMMUNITY_SERVICE_BASE_URL="http://c3",
        AUTH_MOCK_ENABLED=True,
    )
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return FakeResponse(
            {
                "auth_token": "issued-token",
                "user": {
                    "id": 9,
                    "email": "student@shibaura-it.ac.jp",
                    "role": "user",
                }
            }
        )

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    with app.app_context():
        result = AuthServiceClient().login(
            google_auth={
                "email": "student@shibaura-it.ac.jp",
                "mock_email_auth": "1",
                "user_id": "1",
            },
            fallback_auth_token=None,
        )

    assert captured["method"] == "post"
    assert captured["url"] == "http://c3/auth/login"
    assert captured["kwargs"]["json"]["mock_email_auth"] == "1"
    assert result.auth_token == "issued-token"
    assert result.user_id == "9"


def test_auth_service_admin_login_sends_admin_secret(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, AUTH_ADMIN_SECRET="admin-secret")
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return FakeResponse(
            {
                "user": {
                    "id": 4,
                    "email": "admin@shibaura-it.ac.jp",
                    "role": "admin",
                }
            }
        )

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    with app.app_context():
        result = AuthServiceClient(base_url="http://c2").login(
            google_auth={"email": "admin@shibaura-it.ac.jp"},
            fallback_auth_token="token-admin",
            admin=True,
        )

    assert captured["url"] == "http://c2/admin/auth/login"
    assert captured["kwargs"]["json"]["admin_secret"] == "admin-secret"
    assert result.role == "admin"
