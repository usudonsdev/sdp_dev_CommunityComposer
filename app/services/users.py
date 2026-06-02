from app.extensions import db
from app.models.user import User


def create_or_update_user(data: dict) -> User:
    """ユーザーを作成するか、メールアドレスで既存レコードを更新する。"""
    user = User.query.filter_by(email=data["email"]).first()
    if user is None:
        user = User(email=data["email"])
        db.session.add(user)

    user.role = data.get("role", user.role)
    if "auth_token" in data:
        user.auth_token = data["auth_token"]

    db.session.commit()
    return user


def update_user(user: User, data: dict) -> User:
    """ユーザーの項目を更新する。"""
    if "email" in data:
        user.email = data["email"]
    if "role" in data:
        user.role = data["role"]
    if "auth_token" in data:
        user.auth_token = data["auth_token"]

    db.session.commit()
    return user
