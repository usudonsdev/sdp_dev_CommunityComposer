# -*- coding: utf-8 -*-
import os
import warnings
from pathlib import Path

import pytest
from dotenv import load_dotenv


_PLACEHOLDER_VALUES = {
    "",
    "your_google_client_id_here",
    "your_google_client_secret_here",
    "dummy-id",
    "dummy",
    "ここにクライアントシークレットを貼り付け",
}


def _load_project_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
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
    """OAuth クライアント情報が無い環境では警告を出してスキップする."""
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
