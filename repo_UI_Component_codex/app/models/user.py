from datetime import datetime

from app.extensions import db


class User(db.Model):
    """users テーブルに保存されるログイン情報。"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    role = db.Column(db.String(16), nullable=False, default="user")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    auth_token = db.Column(db.String(512), nullable=True)

    communities = db.relationship(
        "Community",
        back_populates="creator",
        lazy=True,
    )

    def to_dict(self) -> dict:
        """JSON にシリアライズ可能な表現を返す。"""
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
        }
