# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Iterable

import requests
from flask import current_app

from app.c1_ui.models import CommunityDetail, CommunityFormData, CommunitySummary


class CommunityServiceUnavailable(RuntimeError):
    """C3コミュニティ活動処理部が未接続の場合に使う例外."""


class CommunityServiceClient:
    """C1 UI処理部からC3コミュニティ活動処理部を呼び出す境界.

    DB仕様が未定のため、このクラスではDB処理を行わない。
    COMMUNITY_SERVICE_BASE_URLが未設定の場合は、画面確認用の仮データだけを返す。
    """

    def __init__(self, base_url: str | None = None):
        configured_url = base_url
        if configured_url is None:
            configured_url = current_app.config.get("COMMUNITY_SERVICE_BASE_URL", "")
        self.base_url = configured_url.rstrip("/")

    def get_community_list(
        self,
        *,
        keyword: str | None,
        category: str | None,
        auth_token: str | None,
    ) -> list[CommunitySummary]:
        if not self.base_url:
            return self._filter_fixture(keyword=keyword, category=category)

        response = requests.get(
            f"{self.base_url}/communities",
            params={"keyword": keyword or "", "category": category or ""},
            headers=self._auth_header(auth_token),
            timeout=5,
        )
        response.raise_for_status()
        return [CommunitySummary(**item) for item in response.json()]

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

        response = requests.get(
            f"{self.base_url}/communities/{community_id}",
            headers=self._auth_header(auth_token),
            timeout=5,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return CommunityDetail(**response.json())

    def save_community(
        self,
        *,
        data: CommunityFormData,
        auth_token: str | None,
        community_id: str | None = None,
    ) -> str:
        if not self.base_url:
            raise CommunityServiceUnavailable("C3コミュニティ活動処理部が未接続である。")

        url = (
            f"{self.base_url}/communities/{community_id}"
            if community_id
            else f"{self.base_url}/communities"
        )
        request_func = requests.put if community_id else requests.post
        response = request_func(
            url,
            json=data.__dict__,
            headers=self._auth_header(auth_token),
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        return str(payload.get("community_id", community_id or ""))

    def delete_community(
        self,
        *,
        community_id: str,
        auth_token: str | None,
    ) -> None:
        if not self.base_url:
            raise CommunityServiceUnavailable("C3コミュニティ活動処理部が未接続である。")

        response = requests.delete(
            f"{self.base_url}/communities/{community_id}",
            headers=self._auth_header(auth_token),
            timeout=5,
        )
        response.raise_for_status()

    @staticmethod
    def _auth_header(auth_token: str | None) -> dict[str, str]:
        if not auth_token:
            return {}
        return {"Authorization": f"Bearer {auth_token}"}

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
                content="週に1回、豊洲キャンパス周辺またはオンラインで活動する。初心者も参加しやすい雰囲気で、UI設計やWeb実装を学ぶ。",
                contact="sit-web@example.com",
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
                content="放課後にフットサルを行う。参加連絡は詳細画面の連絡先から外部ツールで行う。",
                contact="sit-futsal@example.com",
                image_url=None,
                created_at=datetime(2026, 6, 2, 12, 0),
                updated_at=datetime(2026, 6, 8, 12, 0),
            ),
            CommunityDetail(
                community_id="english",
                name="英会話勉強会",
                category="学習",
                summary="昼休みに少人数で練習する活動。",
                content="昼休みに英会話を練習する。授業外の交流を目的とする。",
                contact="sit-english@example.com",
                image_url=None,
                created_at=datetime(2026, 6, 3, 12, 0),
                updated_at=datetime(2026, 6, 8, 12, 0),
            ),
        ]
