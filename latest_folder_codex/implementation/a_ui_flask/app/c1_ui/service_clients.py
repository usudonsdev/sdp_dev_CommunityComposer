# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Iterable

import requests
from flask import current_app

from app.config import config_flag
from app.c1_ui.models import CommunityDetail, CommunityFormData, CommunitySummary


class CommunityServiceUnavailable(RuntimeError):
    """C3コミュニティ活動処理部が未接続の場合に使う例外."""


class CommunityServiceRejected(RuntimeError):
    """C3コミュニティ活動処理部が要求を受け付けなかった場合に使う例外."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class AuthServiceUnavailable(RuntimeError):
    """C2認証処理部が未接続の場合に使う例外."""


class AuthServiceRejected(RuntimeError):
    """C2認証処理部が認証を受け付けなかった場合に使う例外."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class AuthResult:
    def __init__(
        self,
        *,
        auth_token: str,
        user_id: str | None = None,
        email: str | None = None,
        role: str | None = None,
    ):
        self.auth_token = auth_token
        self.user_id = user_id
        self.email = email
        self.role = role


class AuthServiceClient:
    """C1 UI処理部からC2認証処理部を呼び出す境界."""

    def __init__(self, base_url: str | None = None):
        configured_url = base_url
        if configured_url is None:
            configured_url = current_app.config.get("AUTH_SERVICE_BASE_URL", "")
        if not configured_url and config_flag(
            current_app.config.get("AUTH_MOCK_ENABLED")
        ):
            configured_url = current_app.config.get("COMMUNITY_SERVICE_BASE_URL", "")
        self.base_url = configured_url.rstrip("/")

    def login(
        self,
        *,
        google_auth: dict,
        fallback_auth_token: str | None,
        admin: bool = False,
    ) -> AuthResult:
        if not self.base_url:
            raise AuthServiceUnavailable("C2認証処理部が未接続である。")

        endpoint_key = "AUTH_ADMIN_LOGIN_ENDPOINT" if admin else "AUTH_LOGIN_ENDPOINT"
        payload = {
            key: value
            for key, value in google_auth.items()
            if value not in (None, "")
        }
        if admin:
            admin_secret = current_app.config.get("AUTH_ADMIN_SECRET")
            if admin_secret:
                payload.setdefault("admin_secret", admin_secret)

        response = self._request(
            "post",
            f"{self.base_url}{current_app.config[endpoint_key]}",
            json=payload,
        )
        body = response.json()
        return self._auth_result_from_payload(body, fallback_auth_token=None)

    def verify_token(self, auth_token: str | None) -> AuthResult | None:
        if not auth_token or not self.base_url:
            return None
        try:
            response = self._request(
                "get",
                f"{self.base_url}{current_app.config['AUTH_VERIFY_ENDPOINT']}",
                params={"auth_token": auth_token},
            )
        except AuthServiceRejected:
            return None
        except AuthServiceUnavailable:
            if current_app.config.get("TESTING"):
                return AuthResult(auth_token=auth_token)
            return None

        body = response.json()
        return AuthResult(
            auth_token=auth_token,
            user_id=str(body.get("user_id")) if body.get("user_id") is not None else None,
            email=body.get("email"),
            role=body.get("role"),
        )

    def request_magic_link(
        self,
        *,
        email: str,
        verify_base_url: str,
        admin: bool = False,
    ) -> None:
        if not self.base_url:
            raise AuthServiceUnavailable("C2認証処理部が未接続である。")

        endpoint_key = (
            "AUTH_ADMIN_MAGIC_LINK_ENDPOINT" if admin else "AUTH_MAGIC_LINK_ENDPOINT"
        )
        self._request(
            "post",
            f"{self.base_url}{current_app.config[endpoint_key]}",
            json={
                "email": email,
                "verify_base_url": verify_base_url,
            },
        )

    def verify_magic_link(self, *, token: str, admin: bool = False) -> AuthResult:
        if not self.base_url:
            raise AuthServiceUnavailable("C2認証処理部が未接続である。")

        endpoint_key = (
            "AUTH_ADMIN_MAGIC_LINK_VERIFY_ENDPOINT"
            if admin
            else "AUTH_MAGIC_LINK_VERIFY_ENDPOINT"
        )
        response = self._request(
            "get",
            f"{self.base_url}{current_app.config[endpoint_key]}",
            params={"token": token},
        )
        body = response.json()
        return self._auth_result_from_payload(body, fallback_auth_token=None)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        try:
            response = requests.request(method, url, timeout=5, **kwargs)
        except requests.RequestException as exc:
            raise AuthServiceUnavailable("C2認証処理部に接続できない。") from exc

        if response.status_code in {400, 401, 403}:
            raise AuthServiceRejected(
                self._error_message(response),
                status_code=response.status_code,
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise AuthServiceUnavailable("C2認証処理部でエラーが発生した。") from exc
        return response

    @staticmethod
    def _auth_result_from_payload(
        payload: dict,
        *,
        fallback_auth_token: str | None,
    ) -> AuthResult:
        user = payload.get("user") or {}
        auth_token = payload.get("auth_token") or user.get("auth_token")
        if not auth_token:
            raise AuthServiceRejected("C2認証処理部からauth_tokenを取得できない。")
        return AuthResult(
            auth_token=str(auth_token),
            user_id=str(user.get("id")) if user.get("id") is not None else None,
            email=user.get("email") or payload.get("email"),
            role=user.get("role") or payload.get("role"),
        )

    @staticmethod
    def _error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return "C2認証処理部が認証を受け付けなかった。"
        return str(payload.get("error") or payload.get("reason") or "C2認証処理部が認証を受け付けなかった。")


class CommunityServiceClient:
    """C1 UI処理部からC3コミュニティ活動処理部を呼び出す境界.

    DB仕様が未定のため、このクラスではDB処理を行わない。
    COMMUNITY_SERVICE_BASE_URLが未設定の場合は、画面確認用の仮データだけを返す。
    """

    def __init__(self, base_url: str | None = None):
        configured_url = base_url
        if configured_url is None:
            # 環境変数やconfigから取得。なければ同じコンテナ内、またはローカルのAPI（ポート8000など）をデフォルトに
            configured_url = current_app.config.get("COMMUNITY_SERVICE_BASE_URL") or "http://127.0.0.1:8000"
        self.base_url = configured_url.rstrip("/")

    def get_community_list(
        self, *, keyword: str | None, category: str | None, auth_token: str | None,
    ) -> list[CommunitySummary]:
        # base_url が常にある状態にすることで、常に実際のバックエンドAPIへのリクエストを試みるように変更
        response = self._request(
            "get",
            f"{self.base_url}/communities",
            params={
                "q": keyword,
                "category": category,
                "auth_token": auth_token or "",
            },
            auth_token=auth_token,  # _requestが要求するキーワード専用引数として明示的に渡す
        )
        payload = response.json()
        return [self._summary_from_payload(item) for item in payload.get("communities", [])]

    def get_community_detail(
        self,
        *,
        community_id: str,
        auth_token: str | None,
    ) -> CommunityDetail | None:
        if not self.base_url:
            return next(
                (item for item in self._fixture_details() if item.community_id == community_id),
                None,
            )

        response = self._request(
            "get",
            f"{self.base_url}/communities/{community_id}",
            params={"auth_token": auth_token or ""},
            auth_token=auth_token,
            allow_not_found=True,
        )
        if response.status_code == 404:
            return None
        payload = response.json()
        return self._detail_from_payload(payload.get("community", payload))

    def save_community(
        self,
        *,
        data: CommunityFormData,
        auth_token: str | None,
        creator_user_id: str | None = None,
        community_id: str | None = None,
    ) -> str:
        if not self.base_url:
            raise CommunityServiceUnavailable("C3コミュニティ活動処理部が未接続である。")

        url = (
            f"{self.base_url}/communities/{community_id}"
            if community_id
            else f"{self.base_url}/communities"
        )
        response = self._request(
            "put" if community_id else "post",
            url,
            json=self._payload_for_save(
                data=data,
                auth_token=auth_token,
                creator_user_id=creator_user_id,
                include_creator_user_id=community_id is None,
            ),
            auth_token=auth_token,
        )
        payload = response.json()
        community = self._detail_from_payload(payload.get("community", payload))
        return community.community_id

    def upload_image(self, file, auth_token: str | None) -> dict:
        if not self.base_url:
            raise CommunityServiceUnavailable("C3コミュニティ活動処理部が未接続である。")

        url = f"{self.base_url}/communities/images"
        try:
            response = requests.post(
                url,
                files={"image": (file.filename, file.stream, file.mimetype)},
                headers=self._auth_header(auth_token),
                timeout=10,
            )
        except requests.RequestException as exc:
            raise CommunityServiceUnavailable("C3コミュニティ活動処理部に接続できない。") from exc

        if response.status_code in {400, 403, 404}:
            raise CommunityServiceRejected(
                self._error_message(response),
                status_code=response.status_code,
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise CommunityServiceUnavailable("C3コミュニティ活動処理部でエラーが発生した。") from exc
        
        return response.json()

    def delete_community(
        self,
        *,
        community_id: str,
        auth_token: str | None,
    ) -> None:
        if not self.base_url:
            raise CommunityServiceUnavailable("C3コミュニティ活動処理部が未接続である。")

        self._request(
            "delete",
            f"{self.base_url}/communities/{community_id}",
            params={"auth_token": auth_token or ""},
            auth_token=auth_token,
        )

    @staticmethod
    def _auth_header(auth_token: str | None) -> dict[str, str]:
        if not auth_token:
            return {}
        return {"Authorization": f"Bearer {auth_token}"}

    def _request(
        self,
        method: str,
        url: str,
        *,
        auth_token: str | None,
        allow_not_found: bool = False,
        **kwargs,
    ) -> requests.Response:
        try:
            response = requests.request(
                method,
                url,
                headers=self._auth_header(auth_token),
                timeout=5,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise CommunityServiceUnavailable(
                "C3コミュニティ活動処理部に接続できない。"
            ) from exc

        if allow_not_found and response.status_code == 404:
            return response

        if response.status_code in {400, 403, 404}:
            raise CommunityServiceRejected(
                self._error_message(response),
                status_code=response.status_code,
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise CommunityServiceUnavailable(
                "C3コミュニティ活動処理部でエラーが発生した。"
            ) from exc
        return response

    @staticmethod
    def _error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return "C3コミュニティ活動処理部が要求を受け付けなかった。"
        return str(payload.get("error") or "C3コミュニティ活動処理部が要求を受け付けなかった。")

    @staticmethod
    def _normalize_to_api_image_path(image_url: str | None) -> str | None:
        """UIのプロキシURLをAPIが期待する画像パスに戻す。"""
        if not image_url:
            return None
        if image_url.startswith("/api-proxy/uploads/"):
            return "/static/uploads/" + image_url[len("/api-proxy/uploads/") :]
        return image_url

    def _payload_for_save(
        self,
        *,
        data: CommunityFormData,
        auth_token: str | None,
        creator_user_id: str | None = None,
        include_creator_user_id: bool = True,
    ) -> dict:
        payload = {
            "name": data.name,
            "category": data.category,
            "summary": data.summary,
            "content": data.content,
            "auth_token": auth_token,
        }
        image_path = self._normalize_to_api_image_path(data.image_url)
        if image_path is not None:
            payload["image_path"] = image_path
            payload["image_url"] = image_path
        if data.image_format is not None:
            payload["image_format"] = data.image_format
        if data.image_size is not None:
            payload["image_size"] = data.image_size
        configured_creator_user_id = ""
        if include_creator_user_id:
            configured_creator_user_id = (
                creator_user_id or current_app.config.get("COMMUNITY_CREATOR_USER_ID")
            )
        if include_creator_user_id and configured_creator_user_id not in (None, ""):
            try:
                payload["creator_user_id"] = int(configured_creator_user_id)
            except ValueError as exc:
                raise CommunityServiceRejected(
                    "COMMUNITY_CREATOR_USER_IDには数値を設定してください。"
                ) from exc
        return payload

    def _summary_from_payload(self, payload: dict) -> CommunitySummary:
        return CommunitySummary(
            community_id=str(payload.get("community_id") or payload.get("id")),
            name=payload.get("name") or "",
            category=payload.get("category") or "",
            summary=payload.get("summary") or "",
            image_url=self._image_url_from_payload(payload),
            updated_at=self._parse_datetime(payload.get("updated_at")),
            can_edit=bool(payload.get("can_edit", False)),
            can_delete=bool(payload.get("can_delete", False)),
        )

    def _detail_from_payload(self, payload: dict) -> CommunityDetail:
        summary = self._summary_from_payload(payload)
        return CommunityDetail(
            community_id=summary.community_id,
            name=summary.name,
            category=summary.category,
            summary=summary.summary,
            image_url=summary.image_url,
            updated_at=summary.updated_at,
            can_edit=summary.can_edit,
            can_delete=summary.can_delete,
            content=payload.get("content") or "",
            contact=payload.get("contact") or payload.get("contact_email") or "",
            created_at=self._parse_datetime(payload.get("created_at")),
        )

    @staticmethod
    def _parse_datetime(value) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            normalized = value.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(normalized)
            except ValueError:
                pass
        return datetime.utcnow()

    def _image_url_from_payload(self, payload: dict) -> str | None:
        value = payload.get("image_url") or payload.get("image_path")
        if not value:
            return None
        value = str(value)
        if value.startswith(("http://", "https://", "data:")):
            return value
        if value.startswith("/api-proxy/uploads/"):
            value = value.replace("/api-proxy/uploads/", "/static/uploads/")
        if value.startswith("/static/uploads/"):
            return value.replace("/static/uploads/", "/api-proxy/uploads/")
        if not value.startswith("/"):
            return value
        if not self.base_url:
            return value
        return f"{self.base_url}{value}"

    def _filter_fixture(
        self,
        *,
        keyword: str | None,
        category: str | None,
    ) -> list[CommunitySummary]:
        items: Iterable[CommunitySummary] = self._fixture_details()
        if keyword:
            items = [
                item
                for item in items
                if keyword.lower() in item.name.lower() or keyword.lower() in item.summary.lower()
            ]
        if category:
            items = [item for item in items if item.category == category]
        return list(items)

    @staticmethod
    def _fixture_details() -> list[CommunityDetail]:
        return [
            CommunityDetail(
                community_id="web-design",
                name="Web制作研究会",
                category="制作",
                summary="UI設計と実装を一緒に学ぶ。",
                content="週に1回、豊洲キャンパス周辺またはオンラインで活動する。初心者も参加しやすい雰囲気で、UI設計やWeb実装を学ぶ。連絡先: sit-web@example.com",
                contact="",
                image_url=None,
                created_at=datetime(2026, 6, 1, 12, 0),
                updated_at=datetime(2026, 6, 8, 12, 0),
                can_edit=True,
                can_delete=True,
            ),
            CommunityDetail(
                community_id="futsal",
                name="フットサル同好会",
                category="スポーツ",
                summary="週1回、初心者歓迎。",
                content="放課後にフットサルを行う。参加連絡は sit-futsal@example.com から行う。",
                contact="",
                image_url=None,
                created_at=datetime(2026, 6, 2, 12, 0),
                updated_at=datetime(2026, 6, 8, 12, 0),
            ),
            CommunityDetail(
                community_id="english",
                name="英会話勉強会",
                category="学習",
                summary="昼休みに少人数で練習する活動。",
                content="昼休みに英会話を練習する。授業外の交流を目的とする。連絡先: sit-english@example.com",
                contact="",
                image_url=None,
                created_at=datetime(2026, 6, 3, 12, 0),
                updated_at=datetime(2026, 6, 8, 12, 0),
            ),
        ]
