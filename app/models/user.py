from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class User(db.Model):
    """ユーザーモデル"""
    
    __tablename__ = 'users'
    
    # カラム定義
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    auth_token = db.Column(db.String(512), unique=True, nullable=True)