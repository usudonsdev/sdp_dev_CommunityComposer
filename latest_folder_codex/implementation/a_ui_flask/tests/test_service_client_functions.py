from datetime import datetime, timezone

import pytest
import requests

from app import create_app
from app.c1_ui.models import CommunityFormData
from app.c1_ui.service_clients import (
    AuthResult,
    AuthServiceClient,
    AuthServiceRejected,
    AuthServiceUnavailable,
    CommunityServiceClient,
    CommunityServiceRejected,
    CommunityServiceUnavailable,
)


class FakeResponse:
    def __init__(self, payload=None, status_code=200, *, json_error=False, http_error=False):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.json_error = json_error
        self.http_error = http_error

    def json(self):
        if self.json_error:
            raise ValueError("not json")
        return self._payload

    def raise_for_status(self):
        if self.http_error or self.status_code >= 500:
            raise requests.HTTPError("request failed")


def test_auth_result_stores_all_fields():
    result = AuthResult(
        auth_token="token-1",
        user_id="3",
        email="student@shibaura-it.ac.jp",
        role="user",
    )

    assert result.auth_token == "token-1"
    assert result.user_id == "3"
    assert result.email == "student@shibaura-it.ac.jp"
    assert result.role == "user"


def test_auth_service_client_strips_trailing_slash_from_base_url():
    client = AuthServiceClient(base_url="http://c2/")

    assert client.base_url == "http://c2"


def test_auth_service_login_without_base_and_without_fallback_raises_unavailable():
    app = create_app()
    app.config.update(TESTING=True, AUTH_SERVICE_BASE_URL="", AUTH_MOCK_ENABLED=False)

    with app.app_context():
        with pytest.raises(AuthServiceUnavailable) as exc_info:
            AuthServiceClient().login(
                google_auth={"email": "student@shibaura-it.ac.jp"},
                fallback_auth_token=None,
            )

    assert "C2認証処理部が未接続" in str(exc_info.value)


def test_auth_result_from_payload_accepts_top_level_fields():
    result = AuthServiceClient._auth_result_from_payload(
        {"auth_token": "token-1", "email": "student@shibaura-it.ac.jp", "role": "user"},
        fallback_auth_token=None,
    )

    assert result.auth_token == "token-1"
    assert result.email == "student@shibaura-it.ac.jp"
    assert result.role == "user"


def test_auth_result_from_payload_rejects_missing_token():
    with pytest.raises(AuthServiceRejected) as exc_info:
        AuthServiceClient._auth_result_from_payload({}, fallback_auth_token=None)

    assert "auth_token" in str(exc_info.value)


def test_auth_service_request_connection_error_becomes_unavailable(monkeypatch):
    def fake_request(method, url, **kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr("app.c1_ui.service_clients._http_session_request", fake_request)

    with pytest.raises(AuthServiceUnavailable) as exc_info:
        AuthServiceClient(base_url="http://c2")._request("post", "http://c2/auth/login")

    assert "接続できない" in str(exc_info.value)


def test_auth_service_request_plain_rejection_uses_default_message(monkeypatch):
    def fake_request(method, url, **kwargs):
        return FakeResponse(status_code=401, json_error=True)

    monkeypatch.setattr("app.c1_ui.service_clients._http_session_request", fake_request)

    with pytest.raises(AuthServiceRejected) as exc_info:
        AuthServiceClient(base_url="http://c2")._request("post", "http://c2/auth/login")

    assert exc_info.value.status_code == 401
    assert "認証を受け付けなかった" in str(exc_info.value)


def test_auth_service_request_server_error_becomes_unavailable(monkeypatch):
    def fake_request(method, url, **kwargs):
        return FakeResponse(status_code=500)

    monkeypatch.setattr("app.c1_ui.service_clients._http_session_request", fake_request)

    with pytest.raises(AuthServiceUnavailable) as exc_info:
        AuthServiceClient(base_url="http://c2")._request("post", "http://c2/auth/login")

    assert "エラーが発生" in str(exc_info.value)


def test_auth_service_request_smtp_error_becomes_rejected(monkeypatch):
    def fake_request(method, url, **kwargs):
        return FakeResponse(
            {"error": "メール送信に失敗しました: timed out"},
            status_code=503,
        )

    monkeypatch.setattr("app.c1_ui.service_clients._http_session_request", fake_request)

    with pytest.raises(AuthServiceRejected) as exc_info:
        AuthServiceClient(base_url="http://c2")._request(
            "post",
            "http://c2/auth/magic-link",
        )

    assert "メール送信に失敗" in str(exc_info.value)
    assert exc_info.value.status_code == 503


def test_auth_service_error_message_reads_reason_field():
    response = FakeResponse({"reason": "invalid google token"}, status_code=401)

    assert AuthServiceClient._error_message(response) == "invalid google token"


def test_community_service_client_strips_trailing_slash_from_base_url():
    client = CommunityServiceClient(base_url="http://c3/")

    assert client.base_url == "http://c3"


def test_community_auth_header_returns_bearer_token_or_empty_dict():
    assert CommunityServiceClient._auth_header(None) == {}
    assert CommunityServiceClient._auth_header("token-1") == {
        "Authorization": "Bearer token-1"
    }


def test_get_community_detail_returns_none_for_remote_404(monkeypatch):
    def fake_request(method, url, **kwargs):
        return FakeResponse(status_code=404)

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    community = CommunityServiceClient(base_url="http://c3").get_community_detail(
        community_id="missing",
        auth_token="token-1",
    )

    assert community is None


def test_delete_community_calls_expected_endpoint(monkeypatch):
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, kwargs=kwargs)
        return FakeResponse()

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    CommunityServiceClient(base_url="http://c3").delete_community(
        community_id="web-design",
        auth_token="token-1",
    )

    assert captured["method"] == "delete"
    assert captured["url"] == "http://c3/communities/web-design"
    assert captured["kwargs"]["params"] == {"auth_token": "token-1"}
    assert captured["kwargs"]["headers"] == {"Authorization": "Bearer token-1"}


def test_community_request_connection_error_becomes_unavailable(monkeypatch):
    def fake_request(method, url, **kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    with pytest.raises(CommunityServiceUnavailable) as exc_info:
        CommunityServiceClient(base_url="http://c3")._request(
            "get",
            "http://c3/communities",
            auth_token="token-1",
        )

    assert "接続できない" in str(exc_info.value)


def test_community_request_server_error_becomes_unavailable(monkeypatch):
    def fake_request(method, url, **kwargs):
        return FakeResponse(status_code=500)

    monkeypatch.setattr("app.c1_ui.service_clients.requests.request", fake_request)

    with pytest.raises(CommunityServiceUnavailable) as exc_info:
        CommunityServiceClient(base_url="http://c3")._request(
            "get",
            "http://c3/communities",
            auth_token="token-1",
        )

    assert "エラーが発生" in str(exc_info.value)


def test_community_error_message_uses_default_for_non_json_response():
    response = FakeResponse(status_code=400, json_error=True)

    assert (
        CommunityServiceClient._error_message(response)
        == "C3コミュニティ活動処理部が要求を受け付けなかった。"
    )


def test_payload_for_save_uses_creator_user_id_and_image_url():
    app = create_app()
    app.config.update(TESTING=True, COMMUNITY_CREATOR_USER_ID="7")
    data = CommunityFormData(
        name="Web制作研究会",
        category="制作",
        summary="概要",
        content="本文",
        image_url="https://example.test/image.png",
    )

    with app.app_context():
        payload = CommunityServiceClient(base_url="http://c3")._payload_for_save(
            data=data,
            auth_token="token-1",
        )

    assert payload["creator_user_id"] == 7
    assert payload["image_path"] == "https://example.test/image.png"
    assert payload["image_url"] == "https://example.test/image.png"
    assert payload["auth_token"] == "token-1"
    assert "contact" not in payload


def test_payload_for_save_rejects_non_numeric_creator_user_id():
    app = create_app()
    app.config.update(TESTING=True, COMMUNITY_CREATOR_USER_ID="not-number")
    data = CommunityFormData(
        name="Web制作研究会",
        category="制作",
        summary="概要",
        content="本文",
    )

    with app.app_context():
        with pytest.raises(CommunityServiceRejected) as exc_info:
            CommunityServiceClient(base_url="http://c3")._payload_for_save(
                data=data,
                auth_token="token-1",
            )

    assert "数値" in str(exc_info.value)


def test_payload_for_save_normalizes_proxy_image_url_and_omits_blank_image_fields():
    app = create_app()
    app.config.update(TESTING=True, COMMUNITY_CREATOR_USER_ID="7")
    data = CommunityFormData(
        name="Web制作研究会",
        category="制作",
        summary="概要",
        content="本文",
        image_url="/api-proxy/uploads/image.png",
    )

    with app.app_context():
        payload = CommunityServiceClient(base_url="http://c3")._payload_for_save(
            data=data,
            auth_token="token-1",
        )

    assert payload["image_path"] == "/static/uploads/image.png"
    assert payload["image_url"] == "/static/uploads/image.png"
    assert "image_format" not in payload
    assert "image_size" not in payload


def test_summary_from_payload_maps_ids_flags_image_and_datetime():
    client = CommunityServiceClient(base_url="http://c3")

    summary = client._summary_from_payload(
        {
            "id": 12,
            "name": "Web制作研究会",
            "category": "制作",
            "summary": "概要",
            "image_path": "/uploads/web.png",
            "updated_at": "2026-06-08T12:00:00",
            "can_edit": True,
            "can_delete": True,
        }
    )

    assert summary.community_id == "12"
    assert summary.name == "Web制作研究会"
    assert summary.image_url == "http://c3/uploads/web.png"
    assert summary.updated_at == datetime(2026, 6, 8, 12, 0)
    assert summary.can_edit is True
    assert summary.can_delete is True


def test_detail_from_payload_uses_contact_email_and_created_at():
    client = CommunityServiceClient(base_url="http://c3")

    detail = client._detail_from_payload(
        {
            "community_id": "web-design",
            "name": "Web制作研究会",
            "category": "制作",
            "summary": "概要",
            "content": "本文",
            "contact_email": "sit-web@example.com",
            "created_at": "2026-06-01T12:00:00",
            "updated_at": "2026-06-08T12:00:00",
        }
    )

    assert detail.community_id == "web-design"
    assert detail.content == "本文"
    assert detail.contact == "sit-web@example.com"
    assert detail.created_at == datetime(2026, 6, 1, 12, 0)


def test_parse_datetime_accepts_datetime_z_suffix_and_invalid_value():
    original = datetime(2026, 6, 8, 12, 0)
    parsed_z = CommunityServiceClient._parse_datetime("2026-06-08T12:00:00Z")
    parsed_invalid = CommunityServiceClient._parse_datetime("not-a-date")

    assert CommunityServiceClient._parse_datetime(original) is original
    assert parsed_z == datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)
    assert isinstance(parsed_invalid, datetime)


def test_image_url_from_payload_handles_absolute_data_plain_and_root_paths():
    client = CommunityServiceClient(base_url="http://c3")
    no_base_client = CommunityServiceClient(base_url="")

    assert client._image_url_from_payload({}) is None
    assert client._image_url_from_payload({"image_url": "https://example.test/a.png"}) == (
        "https://example.test/a.png"
    )
    assert client._image_url_from_payload({"image_url": "data:image/png;base64,aaa"}) == (
        "data:image/png;base64,aaa"
    )
    assert client._image_url_from_payload({"image_path": "uploads/a.png"}) == "uploads/a.png"
    assert client._image_url_from_payload({"image_path": "/uploads/a.png"}) == (
        "http://c3/uploads/a.png"
    )
    assert client._image_url_from_payload({"image_path": "/api-proxy/uploads/a.png"}) == (
        "/api-proxy/uploads/a.png"
    )
    assert no_base_client._image_url_from_payload({"image_path": "/uploads/a.png"}) == (
        "/uploads/a.png"
    )


def test_filter_fixture_filters_by_keyword_and_category():
    client = CommunityServiceClient(base_url="")

    keyword_result = client._filter_fixture(keyword="Web", category=None)
    category_result = client._filter_fixture(keyword=None, category="スポーツ")
    no_match = client._filter_fixture(keyword="存在しない", category=None)

    assert [item.community_id for item in keyword_result] == ["web-design"]
    assert [item.community_id for item in category_result] == ["futsal"]
    assert no_match == []


def test_fixture_details_returns_editable_web_design_item():
    details = CommunityServiceClient._fixture_details()

    web_design = details[0]
    assert web_design.community_id == "web-design"
    assert web_design.can_edit is True
    assert web_design.can_delete is True
    assert "連絡先:" in web_design.content
