from app.extensions import db
from app.models.user import User
from app.services.password_service import hash_password


def create_or_update_user(data: dict) -> User:
    """ユーザーを作成するか、メールアドレスで既存レコードを更新する。"""
    email = data.get("email")
    if not email:
        raise ValueError("email is required")

    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(email=email)
        db.session.add(user)

    user.role = data.get("role", user.role)
    if "auth_token" in data:
        user.auth_token = data["auth_token"]
    if data.get("password"):
        user.password_hash = hash_password(str(data["password"]))

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
    if data.get("password"):
        user.password_hash = hash_password(str(data["password"]))

    db.session.commit()
    return user
