from secrets import compare_digest

from flask import Blueprint, abort, current_app, jsonify, request

from app.extensions import db
from app.models.user import User
from app.services.users import create_or_update_user, update_user


users_bp = Blueprint("users", __name__)


@users_bp.post("/auth/login")
def login_user():
    """一般ユーザーのログイン情報を作成または更新する。"""
    data = request.get_json(silent=True) or {}
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
