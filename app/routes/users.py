from datetime import datetime
from secrets import compare_digest

from flask import Blueprint, abort, current_app, jsonify, request

from app.extensions import db
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.users import create_or_update_user, update_user


users_bp = Blueprint("users", __name__)


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
    try:
        user = create_or_update_user({"email": email, "role": "user"})
    except ValueError:
        return {"error": "invalid request payload"}, 400

    if admin and user.role != "admin":
        return jsonify({"error": "管理者権限がありません。"}), 403

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

    data["role"] = "user"

    try:
        user = create_or_update_user(data)
    except ValueError:
        return jsonify({"error": "invalid request payload"}), 400
    return jsonify({"user": user.to_dict()}), 200


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

    admin_login_secret = current_app.config.get("ADMIN_LOGIN_SECRET")
    provided_secret = data.get("admin_secret")
    if (
        not admin_login_secret
        or not isinstance(provided_secret, str)
        or not compare_digest(provided_secret, admin_login_secret)
    ):
        abort(403)

    data["role"] = "admin"
    try:
        user = create_or_update_user(data)
    except ValueError:
        return jsonify({"error": "invalid request payload"}), 400

    return jsonify({"user": user.to_dict()}), 200


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
