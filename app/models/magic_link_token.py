from datetime import datetime

from app.extensions import db


class MagicLinkToken(db.Model):
    """メールマジックリンク用のワンタイムトークン。"""

    __tablename__ = "magic_link_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    admin = db.Column(db.Boolean, nullable=False, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
