from datetime import datetime, timedelta
import secrets
from threading import Lock

from flask import current_app
from google.auth.transport import requests
from google.oauth2 import id_token

from app.extensions import db
from app.models import User

_VERIFY_CACHE: dict[str, tuple[datetime, dict]] = {}
_VERIFY_CACHE_LOCK = Lock()



def _verify_cache_ttl_seconds() -> int:
    raw = current_app.config.get("AUTH_VERIFY_CACHE_TTL_SECONDS", 30)
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 30


def _get_cached_verify(auth_token: str, c_time: datetime) -> dict | None:
    ttl = _verify_cache_ttl_seconds()
    if ttl <= 0:
        return None
    with _VERIFY_CACHE_LOCK:
        cached = _VERIFY_CACHE.get(auth_token)
    if cached is None:
        return None
    cached_at, payload = cached
    if (c_time - cached_at).total_seconds() > ttl:
        with _VERIFY_CACHE_LOCK:
            _VERIFY_CACHE.pop(auth_token, None)
        return None
    expires_at = payload.get("_token_expires_at")
    if expires_at and c_time > expires_at:
        with _VERIFY_CACHE_LOCK:
            _VERIFY_CACHE.pop(auth_token, None)
        return None
    return {key: value for key, value in payload.items() if not key.startswith("_")}


def _set_cached_verify(auth_token: str, c_time: datetime, payload: dict) -> None:
    ttl = _verify_cache_ttl_seconds()
    if ttl <= 0 or payload.get("status") != "OK":
        return
    cache_payload = dict(payload)
    with _VERIFY_CACHE_LOCK:
        _VERIFY_CACHE[auth_token] = (c_time, cache_payload)


class AuthService:
    """
    大学GoogleアカウントのGoogle認証情報を検証し、
    メールアドレスが@shibaura-it.ac.jpであることを確認する。
    認証後、管理者権限確認とログイントークン発行を行う。
    """

    def verify_google_account(self, google_auth: dict) -> dict:
        """
        Google認証情報を検証し、@shibaura-it.ac.jp であることを確認
        入力: google_auth (フロントから送信された {'id_token': 'xxxx'} などの辞書)
        出力: 認証結果（dict: OK/NG、ユーザID、メールアドレス）
        """
        # フロントエンドから送られてきたIDトークンを取り出す
        token = google_auth.get('id_token')
        if not token:
            return {"status": "NG", "reason": "トークンが存在しません"}
        
        try:
            # 追加: current_app経由で設定からクライアントIDを取得
            client_id = (current_app.config.get("GOOGLE_CLIENT_ID") or "").strip()

            if not client_id:
                return {"status": "NG", "reason": "サーバーの認証設定が不足しています"}

            # Docker/VM ではホストと数秒ずれることがあるため許容する
            id_info = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                client_id,
                clock_skew_in_seconds=60,
            )
            
            email = id_info.get("email")
            if not id_info.get("email_verified", False):
                return {"status": "NG", "reason": "メールアドレスが確認済みではありません。"}

            hosted_domain = (
                current_app.config.get("GOOGLE_HOSTED_DOMAIN", "shibaura-it.ac.jp") or ""
            ).strip().lower()
            token_hd = (id_info.get("hd") or "").strip().lower()
            if token_hd and token_hd != hosted_domain:
                return {"status": "NG", "reason": "芝浦工業大学のGoogleアカウントではありません"}

            if not email or not email.endswith(f"@{hosted_domain}"):
                return {"status": "NG", "reason": "芝浦工業大学のGoogleアカウントではありません"}
            
            try:
                # DBからこのメールアドレスを持つユーザーを検索
                user = User.query.filter_by(email=email).first()
                
                # 初めてのログインなら新規登録
                if not user:
                    user = User(email=email, role="user") # roleはデフォルトで"user"
                    db.session.add(user)
                    db.session.commit()  # ここでSQLiteに保存され、自動で user.id が採番される
                
                # 確定した本物の id を取得
                user_id = user.id
                
            except Exception as e:
                # DB接続エラーやクエリエラーなどが発生した場合のハンドリング
                db.session.rollback()
                return {"status": "NG", "reason": f"データベースエラーが発生しました: {str(e)}"}
            
            return {
                "status": "OK",
                "user_id": user_id,
                "email": email
            }
            
        except ValueError as exc:
            # トークンが無効、期限切れ、audience不一致など
            return {
                "status": "NG",
                "reason": f"Google認証の検証に失敗しました: {exc}",
            }
    

    def verify_admin_role(self, user_id: int) -> dict:
        """
        ユーザが管理者権限を持つかを確認
        入力: ユーザID
        出力: 管理者認証結果OK/NG、権限種別
        """
        try:
            # DBからユーザIDに対応するユーザを取得
            user = db.session.get(User, user_id)

            # ユーザが見つからない場合
            if not user:
                return {
                    "status": "NG",
                    "reason": "ユーザが見つかりません",
                    "role": None
                }
            
            # ユーザが見つかった場合、roleを確認
            is_admin = (user.role == "admin")

            if is_admin:
                return {
                    "status": "OK",
                    "role": user.role
                }
            else:
                return {
                    "status": "NG",
                    "reason": "管理者権限がありません",
                    "role": user.role
                }
            
        except Exception as e:
            return {
                "status": "NG",
                "reason": f"エラーが発生しました: {str(e)}",
                "role": None
            }

    def issue_login_token(self, user_id: int, c_time) -> dict:
        """
        本システム内で利用するauth_tokenを発行
        入力: ユーザID、現在時刻
        出力: auth_token、有効期限、F1ログイン情報の更新結果
        """
        try:
            # 安全なランダムな文字列（トークン）を生成 (64文字)
            token = secrets.token_urlsafe(48)
            
            # DBから対象ユーザーを取得
            user = db.session.get(User, user_id)
            if not user:
                return {
                    "status": "NG",
                    "reason": "ユーザーが見つかりません。",
                    "auth_token": None
                }
            
            # トークンの有効期限を設定（発行から24時間後）
            expires_at = c_time + timedelta(hours=24)

            old_token = user.auth_token
            # ユーザーレコードの auth_token を更新
            user.auth_token = token
            user.token_expires_at = expires_at
            db.session.commit()
            if old_token:
                with _VERIFY_CACHE_LOCK:
                    _VERIFY_CACHE.pop(old_token, None)

            return {
                "status": "OK",
                "auth_token": token,
                "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                "status": "NG",
                "reason": f"トークン発行中にデータベースエラーが発生しました: {str(e)}",
                "auth_token": None
            }

    def verify_login_token(self, auth_token: str, c_time) -> dict:
        """
        auth_tokenの有効性を検証
        入力: auth_token, 現在時刻
        出力: 認証結果OK/NG、ユーザID、権限種別
        """
        try:
            if not auth_token:
                return {"status": "NG", "reason": "トークンがありません。"}

            cached = _get_cached_verify(auth_token, c_time)
            if cached is not None:
                return cached

            # DBからトークンに一致するユーザーを検索
            user = User.query.filter_by(auth_token=auth_token).first()

            if not user:
                return {"status": "NG", "reason": "無効なトークンです。"}

            # トークンの有効期限を確認
            if user.token_expires_at and c_time > user.token_expires_at:
                return {
                    "status": "NG",
                    "reason": "セッションの有効期限が切れています。",
                    "user_id": None, "role": None, "email": None
                }

            # 期限内ならOK
            result = {
                "status": "OK",
                "user_id": user.id,
                "role": user.role,
                "email": user.email,
                "_token_expires_at": user.token_expires_at,
            }
            _set_cached_verify(auth_token, c_time, result)
            return {
                key: value for key, value in result.items() if not key.startswith("_")
            }
        except Exception as e:
            return {"status": "NG", "reason": str(e)}
