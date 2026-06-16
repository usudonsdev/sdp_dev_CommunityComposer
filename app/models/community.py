from datetime import datetime

from app.extensions import db


class Community(db.Model):
    """communities テーブルに保存されるコミュニティ情報。"""

    __tablename__ = "communities"

    STATUS_PUBLIC = "public"
    STATUS_PRIVATE = "private"
    STATUS_DELETED = "deleted"

    id = db.Column(db.Integer, primary_key=True)
    creator_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(99), nullable=False)
    category = db.Column(db.String(63), nullable=False)
    summary = db.Column(db.String(511), nullable=True)
    content = db.Column(db.String(3999), nullable=False)
    image_path = db.Column(db.String(511), nullable=True)
    image_format = db.Column(db.String(8), nullable=True)
    image_size = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(16), nullable=False, default=STATUS_PUBLIC)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    creator = db.relationship("User", back_populates="communities")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self) -> dict:
        """JSON にシリアライズ可能な表現を返す。"""
        return {
            "id": self.id,
            "creator_user_id": self.creator_user_id,
            "name": self.name,
            "category": self.category,
            "summary": self.summary,
            "content": self.content,
            "image_path": self.image_path,
            "image_format": self.image_format,
            "image_size": self.image_size,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
