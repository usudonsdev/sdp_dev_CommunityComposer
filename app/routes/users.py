from datetime import datetime

from flask import Blueprint, abort, jsonify, request

from app.extensions import db
from app.models.user import User
from app.services.admin_emails import is_admin_email
from app.services.auth_service import AuthService
from app.services.email_service import EmailDeliveryError, smtp_configured
from app.services.magic_link_service import (
    MagicLinkError,
    create_and_send_magic_link,
    verify_magic_link_token,
)
from app.services.password_service import validate_password, verify_password
from app.services.users import create_or_update_user, update_user


users_bp = Blueprint("users", __name__)

UNIVERSITY_EMAIL_DOMAIN = "@shibaura-it.ac.jp"


def _validate_university_email(email: str) -> str | None:
    normalized = (email or "").strip().lower()
    if not normalized or "@" not in normalized:
        return "メールアドレスを入力してください。"
    if not normalized.endswith(UNIVERSITY_EMAIL_DOMAIN):
        return "芝浦工業大学のメールアドレス（@shibaura-it.ac.jp）のみ利用できます。"
    return None


def _user_payload_for_email(email: str) -> dict:
    normalized = email.strip().lower()
    payload = {"email": normalized}
    if is_admin_email(normalized):
        payload["role"] = "admin"
    return payload


def _issue_auth_response(*, user: User) -> tuple[dict, int]:
    token_result = AuthService().issue_login_token(
        user_id=user.id,
        c_time=datetime.utcnow(),
    )
    if token_result["status"] != "OK":
        return (
            {"error": token_result.get("reason", "ログイントークンの発行に失敗しました。")},
            500,
        )

    db.session.refresh(user)
    return (
        {
            "user": user.to_dict(),
            "auth_token": token_result["auth_token"],
            "email": user.email,
        },
        200,
    )


def _register_with_password(*, email: str, password: str, admin: bool) -> tuple[dict, int]:
    validation_error = _validate_university_email(email)
    if validation_error:
        return {"error": validation_error}, 400

    password_error = validate_password(password)
    if password_error:
        return {"error": password_error}, 400

    normalized_email = email.strip().lower()
    existing = User.query.filter_by(email=normalized_email).first()
    if existing and existing.password_hash:
        return {"error": "このメールアドレスは既に登録されています。"}, 409

    payload = _user_payload_for_email(normalized_email)
    payload["password"] = password

    try:
        user = create_or_update_user(payload)
    except ValueError:
        return {"error": "invalid request payload"}, 400

    if admin and user.role != "admin":
        return {"error": "管理者権限がありません。"}, 403

    body, status_code = _issue_auth_response(user=user)
    if status_code == 200:
        body["message"] = "登録が完了しました。"
    return body, status_code


def _login_with_password(*, email: str, password: str, admin: bool) -> tuple[dict, int]:
    validation_error = _validate_university_email(email)
    if validation_error:
        return {"error": validation_error}, 400

    if not password:
        return {"error": "パスワードを入力してください。"}, 400

    normalized_email = email.strip().lower()
    user = User.query.filter_by(email=normalized_email).first()
    if user is None or not user.password_hash:
        return {"error": "メールアドレスまたはパスワードが正しくありません。"}, 401

    if not verify_password(user.password_hash, password):
        return {"error": "メールアドレスまたはパスワードが正しくありません。"}, 401

    if admin and user.role != "admin":
        return {"error": "管理者権限がありません。"}, 403

    return _issue_auth_response(user=user)


def _login_with_google_id_token(*, id_token: str, admin: bool) -> tuple[dict, int]:
    auth_service = AuthService()
    verify_result = auth_service.verify_google_account({"id_token": id_token})
    if verify_result["status"] != "OK":
        return (
            {"error": verify_result.get("reason", "Google認証の検証に失敗しました。")},
            401,
        )

    user_id = verify_result["user_id"]
    if admin:
        admin_result = auth_service.verify_admin_role(user_id)
        if admin_result["status"] != "OK":
            return (
                {
                    "error": admin_result.get(
                        "reason",
                        "管理者権限がありません。",
                    )
                },
                403,
            )

    token_result = auth_service.issue_login_token(
        user_id=user_id,
        c_time=datetime.utcnow(),
    )
    if token_result["status"] != "OK":
        return (
            {"error": token_result.get("reason", "ログイントークンの発行に失敗しました。")},
            500,
        )

    user = db.session.get(User, user_id)
    return (
        {
            "user": user.to_dict(),
            "auth_token": token_result["auth_token"],
            "email": verify_result["email"],
        },
        200,
    )


def _login_with_mock_email(*, email: str, admin: bool) -> tuple[dict, int]:
    validation_error = _validate_university_email(email)
    if validation_error:
        return {"error": validation_error}, 400

    try:
        user = create_or_update_user(_user_payload_for_email(email))
    except ValueError:
        return {"error": "invalid request payload"}, 400

    if admin and user.role != "admin":
        return {"error": "管理者権限がありません。"}, 403

    return _issue_auth_response(user=user)


@users_bp.post("/auth/register")
def register_user():
    """大学メールアドレスとパスワードでユーザーを登録する。"""
    data = request.get_json(silent=True) or {}
    body, status_code = _register_with_password(
        email=str(data.get("email", "")),
        password=str(data.get("password", "")),
        admin=False,
    )
    return jsonify(body), status_code


@users_bp.post("/admin/auth/register")
def register_admin():
    """管理者メールアドレスとパスワードで管理者を登録する。"""
    data = request.get_json(silent=True) or {}
    body, status_code = _register_with_password(
        email=str(data.get("email", "")),
        password=str(data.get("password", "")),
        admin=True,
    )
    return jsonify(body), status_code


@users_bp.post("/auth/login")
def login_user():
    """一般ユーザーのログイン情報を作成または更新する。"""
    data = request.get_json(silent=True) or {}
    id_token = data.get("id_token")
    if id_token:
        body, status_code = _login_with_google_id_token(id_token=id_token, admin=False)
        return jsonify(body), status_code
    if data.get("mock_email_auth"):
        body, status_code = _login_with_mock_email(
            email=str(data.get("email", "")),
            admin=False,
        )
        return jsonify(body), status_code

    password = data.get("password")
    if password is not None and str(password) != "":
        body, status_code = _login_with_password(
            email=str(data.get("email", "")),
            password=str(password),
            admin=False,
        )
        return jsonify(body), status_code

    email = str(data.get("email", "")).strip()
    validation_error = _validate_university_email(email)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    return jsonify({"error": "パスワードを入力してください。"}), 400


def _request_magic_link(*, email: str, verify_base_url: str, admin: bool) -> tuple[dict, int]:
    validation_error = _validate_university_email(email)
    if validation_error:
        return {"error": validation_error}, 400

    if not verify_base_url:
        return {"error": "verify_base_url が必要です。"}, 400

    if admin:
        try:
            user = create_or_update_user(_user_payload_for_email(email))
        except ValueError:
            return {"error": "invalid request payload"}, 400
        if user.role != "admin":
            return {"error": "管理者権限がありません。"}, 403

    if not smtp_configured():
        return {"error": "メール送信が未設定です。"}, 503

    try:
        create_and_send_magic_link(
            email=email,
            verify_base_url=verify_base_url,
            admin=admin,
        )
    except EmailDeliveryError as exc:
        return {"error": str(exc)}, 503

    return (
        {
            "message": "ログインリンクをメールで送信しました。",
            "email": email.strip().lower(),
        },
        200,
    )


def _verify_magic_link(*, token: str) -> tuple[dict, int]:
    try:
        body = verify_magic_link_token(token=token)
    except MagicLinkError as exc:
        return {"error": exc.message}, exc.status_code
    return body, 200


@users_bp.post("/auth/magic-link")
def request_magic_link():
    """一般ユーザー向けマジックリンクをメール送信する。"""
    data = request.get_json(silent=True) or {}
    body, status_code = _request_magic_link(
        email=str(data.get("email", "")),
        verify_base_url=str(data.get("verify_base_url", "")).strip(),
        admin=False,
    )
    return jsonify(body), status_code


@users_bp.get("/auth/magic-link/verify")
def verify_magic_link():
    """マジックリンクを検証し auth_token を返す。"""
    body, status_code = _verify_magic_link(token=request.args.get("token") or "")
    return jsonify(body), status_code


@users_bp.post("/admin/auth/magic-link")
def request_admin_magic_link():
    """管理者向けマジックリンクをメール送信する。"""
    data = request.get_json(silent=True) or {}
    body, status_code = _request_magic_link(
        email=str(data.get("email", "")),
        verify_base_url=str(data.get("verify_base_url", "")).strip(),
        admin=True,
    )
    return jsonify(body), status_code


@users_bp.get("/admin/auth/magic-link/verify")
def verify_admin_magic_link():
    """管理者向けマジックリンクを検証し auth_token を返す。"""
    body, status_code = _verify_magic_link(token=request.args.get("token") or "")
    return jsonify(body), status_code


@users_bp.get("/auth/verify")
def verify_auth_token():
    """発行済みauth_tokenの有効性を検証する。"""
    auth_token = request.args.get("auth_token") or ""
    result = AuthService().verify_login_token(
        auth_token=auth_token,
        c_time=datetime.utcnow(),
    )
    if result["status"] != "OK":
        return jsonify({"error": result.get("reason", "無効なトークンです。")}), 401
    return jsonify(
        {
            "user_id": result["user_id"],
            "email": result["email"],
            "role": result["role"],
        }
    ), 200


@users_bp.post("/users")
def post_user():
    """ユーザーのログイン情報を作成または更新する。"""
    data = request.get_json(silent=True) or {}

    try:
        data["role"] = "user"
        user = create_or_update_user(data)
    except ValueError:
        return jsonify({"error": "invalid request payload"}), 400
    return jsonify({"user": user.to_dict()}), 201


@users_bp.post("/admin/auth/login")
def login_admin():
    """管理者のログイン情報を作成または更新する。"""
    data = request.get_json(silent=True) or {}
    id_token = data.get("id_token")
    if id_token:
        body, status_code = _login_with_google_id_token(id_token=id_token, admin=True)
        return jsonify(body), status_code
    if data.get("mock_email_auth"):
        body, status_code = _login_with_mock_email(
            email=str(data.get("email", "")),
            admin=True,
        )
        return jsonify(body), status_code

    password = data.get("password")
    if password is not None and str(password) != "":
        body, status_code = _login_with_password(
            email=str(data.get("email", "")),
            password=str(password),
            admin=True,
        )
        return jsonify(body), status_code

    email = str(data.get("email", "")).strip()
    validation_error = _validate_university_email(email)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    return jsonify({"error": "パスワードを入力してください。"}), 400


@users_bp.get("/users/<int:user_id>")
def get_user(user_id: int):
    """1人分のログイン情報を返す。"""
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    return jsonify({"user": user.to_dict()}), 200


@users_bp.put("/users/<int:user_id>")
def put_user(user_id: int):
    """1人分のログイン情報を更新する。"""
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    data = request.get_json(silent=True) or {}

    updated = update_user(user, data)
    return jsonify({"user": updated.to_dict()}), 200
