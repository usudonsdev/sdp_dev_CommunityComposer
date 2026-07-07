# -*- coding: utf-8 -*-
import os
import warnings
from pathlib import Path

import pytest

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional for lightweight UI test envs
    def load_dotenv(*_args, **_kwargs):
        return False

from app.c1_ui import routes
from app.c1_ui.service_clients import CommunityServiceClient


_PLACEHOLDER_VALUES = {
    "",
    "your_google_client_id_here",
    "your_google_client_secret_here",
    "dummy-id",
    "dummy",
    "ここにクライアントシークレットを貼り付け",
}


def _load_project_env() -> None:
    env_path = Path(__file__).resolve().parents[4] / ".env"
    if env_path.is_file():
        load_dotenv(env_path)


_load_project_env()


def is_google_oauth_configured() -> bool:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    return (
        client_id not in _PLACEHOLDER_VALUES
        and client_secret not in _PLACEHOLDER_VALUES
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "email_auth: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET が必要なメール認証テスト",
    )


@pytest.fixture
def google_oauth_credentials():
    if is_google_oauth_configured():
        return {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", "").strip(),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
        }

    warnings.warn(
        "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET が未設定のため、"
        "メール認証テストをスキップします。",
        UserWarning,
        stacklevel=2,
    )
    pytest.skip(
        "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET が未設定のため、"
        "メール認証テストをスキップします。"
    )


@pytest.fixture
def fixture_community_service(monkeypatch):
    """HTTPバックエンドなしで画面テストできるよう、fixtureデータを返す."""
    fixtures = CommunityServiceClient._fixture_details()

    class FixtureCommunityServiceClient:
        def get_community_list(self, *, keyword, category, auth_token):
            items = list(fixtures)
            if keyword:
                items = [
                    item
                    for item in items
                    if keyword.lower() in item.name.lower()
                    or keyword.lower() in item.summary.lower()
                ]
            if category:
                items = [item for item in items if item.category == category]
            return items

        def get_community_detail(self, *, community_id, auth_token):
            return next(
                (item for item in fixtures if item.community_id == community_id),
                None,
            )

        def save_community(self, **kwargs):
            return kwargs.get("community_id") or "new-community"

        def delete_community(self, **kwargs):
            return None

    monkeypatch.setattr(routes, "CommunityServiceClient", FixtureCommunityServiceClient)
