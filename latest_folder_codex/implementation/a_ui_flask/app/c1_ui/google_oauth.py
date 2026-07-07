# -*- coding: utf-8 -*-
from urllib.parse import urlencode

import requests
from flask import current_app, url_for


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

_PLACEHOLDER_VALUES = {
    "",
    "your_google_client_id_here",
    "your_google_client_secret_here",
    "dummy-id",
    "dummy",
    "ここにクライアントシークレットを貼り付け",
}


def _is_configured_oauth_value(value: str | None) -> bool:
    if not value:
        return False
    return value.strip() not in _PLACEHOLDER_VALUES


def google_oauth_configured() -> bool:
    return (
        _is_configured_oauth_value(current_app.config.get("GOOGLE_CLIENT_ID"))
        and _is_configured_oauth_value(current_app.config.get("GOOGLE_CLIENT_SECRET"))
    )


def _redirect_uri(*, admin: bool) -> str:
    configured = current_app.config.get("GOOGLE_OAUTH_REDIRECT_URI")
    if configured:
        return configured
    endpoint = (
        "c1_ui.handle_admin_google_oauth_callback"
        if admin
        else "c1_ui.handle_google_oauth_callback"
    )
    return url_for(endpoint, _external=True)


def build_authorize_url(*, admin: bool) -> str:
    params = {
        "client_id": current_app.config["GOOGLE_CLIENT_ID"],
        "redirect_uri": _redirect_uri(admin=admin),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "hd": current_app.config.get("GOOGLE_HOSTED_DOMAIN", "shibaura-it.ac.jp"),
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_id_token(*, code: str, admin: bool) -> dict:
    try:
        response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": current_app.config["GOOGLE_CLIENT_ID"],
                "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
                "redirect_uri": _redirect_uri(admin=admin),
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError("Google認証トークンの取得に失敗した。") from exc

    payload = response.json()
    id_token = payload.get("id_token")
    if not id_token:
        raise ValueError("Google認証からid_tokenを取得できない。")
    return payload
