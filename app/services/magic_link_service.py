from datetime import datetime, timedelta
from secrets import token_urlsafe

from flask import current_app

from app.extensions import db
from app.models.magic_link_token import MagicLinkToken
from app.services.auth_service import AuthService
from app.services.email_service import EmailDeliveryError, send_magic_link_email
from app.services.users import create_or_update_user


class MagicLinkError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _token_lifetime_minutes() -> int:
    raw = current_app.config.get("MAGIC_LINK_EXPIRE_MINUTES", 15)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 15


def create_and_send_magic_link(
    *,
    email: str,
    verify_base_url: str,
    admin: bool = False,
) -> None:
    normalized_email = email.strip().lower()
    token = token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=_token_lifetime_minutes())

    db.session.add(
        MagicLinkToken(
            token=token,
            email=normalized_email,
            admin=admin,
            expires_at=expires_at,
        )
    )

    base = verify_base_url.rstrip("/")
    verify_path = (
        "/admin/auth/email/verify" if admin else "/auth/email/verify"
    )
    verify_url = f"{base}{verify_path}?token={token}"

    try:
        send_magic_link_email(to_email=normalized_email, verify_url=verify_url)
    except EmailDeliveryError:
        db.session.rollback()
        raise

    db.session.commit()


def verify_magic_link_token(*, token: str) -> dict:
    if not token:
        raise MagicLinkError("ログインリンクが無効です。", status_code=400)

    record = MagicLinkToken.query.filter_by(token=token).first()
    now = datetime.utcnow()
    if record is None:
        raise MagicLinkError("ログインリンクが無効です。", status_code=400)
    if record.used_at is not None:
        raise MagicLinkError("このログインリンクは既に使用されています。", status_code=400)
    if now > record.expires_at:
        raise MagicLinkError("ログインリンクの有効期限が切れています。", status_code=400)

    try:
        user = create_or_update_user({"email": record.email})
    except ValueError as exc:
        raise MagicLinkError("ログインに失敗しました。", status_code=400) from exc

    if record.admin and user.role != "admin":
        raise MagicLinkError("管理者権限がありません。", status_code=403)

    token_result = AuthService().issue_login_token(user_id=user.id, c_time=now)
    if token_result["status"] != "OK":
        raise MagicLinkError(
            token_result.get("reason", "ログイントークンの発行に失敗しました。"),
            status_code=500,
        )

    record.used_at = now
    db.session.commit()
    db.session.refresh(user)

    return {
        "user": user.to_dict(),
        "auth_token": token_result["auth_token"],
        "email": user.email,
    }
