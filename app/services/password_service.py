from werkzeug.security import check_password_hash, generate_password_hash


MIN_PASSWORD_LENGTH = 8


def validate_password(password: str) -> str | None:
    if not password or not str(password).strip():
        return "パスワードを入力してください。"
    if len(str(password)) < MIN_PASSWORD_LENGTH:
        return f"パスワードは{MIN_PASSWORD_LENGTH}文字以上にしてください。"
    return None


def hash_password(password: str) -> str:
    return generate_password_hash(str(password))


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    return check_password_hash(password_hash, str(password))
