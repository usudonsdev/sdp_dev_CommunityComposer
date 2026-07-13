from datetime import datetime

from app.extensions import db


class User(db.Model):
    """users テーブルに保存されるログイン情報。"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True) # ユーザーID（自動生成される整数の主キー）
    email = db.Column(db.String(255), nullable=False, unique=True, index=True) # メールアドレス
    role = db.Column(db.String(16), nullable=False, default="user") # ロール（例: "user", "admin"）
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # 登録日時
    auth_token = db.Column(db.String(512), nullable=True) # 認証トークン
    token_expires_at = db.Column(db.DateTime, nullable=True) # トークンの有効期限
    password_hash = db.Column(db.String(255), nullable=True)

    communities = db.relationship(
        "Community",
        back_populates="creator",
        lazy=True,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self) -> dict:
        """JSON にシリアライズ可能な表現を返す。"""
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
        }
