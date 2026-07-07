from app.extensions import db
from app.models.community import Community


def list_communities() -> list[Community]:
    """コミュニティ一覧を返す。"""
    return Community.query.order_by(Community.updated_at.desc()).limit(100).all()


def create_community(data: dict) -> Community:
    """コミュニティレコードを作成する。"""
    required_fields = ["creator_user_id", "name", "category", "content"]
    missing_fields = [field for field in required_fields if data.get(field) in (None, "")]
    if missing_fields:
        raise ValueError(f"missing required fields: {', '.join(missing_fields)}")

    community = Community(
        creator_user_id=data["creator_user_id"],
        name=data["name"],
        category=data["category"],
        summary=data.get("summary"),
        content=data["content"],
        image_path=data.get("image_path"),
        image_format=data.get("image_format"),
        image_size=data.get("image_size"),
        status=data.get("status", Community.STATUS_PUBLIC),
    )
    db.session.add(community)
    db.session.commit()
    return community


def update_community(community: Community, data: dict) -> Community:
    """コミュニティレコードを更新する。"""
    fields = [
        "creator_user_id",
        "name",
        "category",
        "summary",
        "content",
        "image_path",
        "image_format",
        "image_size",
        "status",
    ]
    for field in fields:
        if field in data:
            setattr(community, field, data[field])
    db.session.commit()
    return community


def delete_community(community: Community) -> dict:
    """コミュニティレコードを削除する。"""
    community_dict = community.to_dict()
    db.session.delete(community)
    db.session.commit()
    return community_dict
from sqlalchemy import or_

from app.extensions import db
from app.models.community import Community
from app.models.user import User


class CommunityService:
    """コミュニティ活動処理部のサービス。"""

    MAX_RESULTS = 100
    _TEXT_LIMITS = {
        "name": 99,
        "category": 63,
        "summary": 511,
        "content": 3999,
        "image_path": 511,
        "image_format": 8,
    }

    @staticmethod
    def _get_user_by_auth_token(auth_token: str | None) -> User | None:
        if not auth_token:
            return None
        return User.query.filter_by(auth_token=auth_token).first()

    @classmethod
    def _resolve_actor(cls, data: dict) -> User | None:
        auth_token = data.get("auth_token")
        user = cls._get_user_by_auth_token(auth_token)
        if user is not None:
            return user

        creator_user_id = data.get("creator_user_id")
        if creator_user_id in (None, ""):
            return None
        return db.session.get(User, creator_user_id)

    @classmethod
    def _validate_payload(cls, data: dict, *, is_update: bool = False) -> None:
        if is_update:
            editable_fields = [
                "name",
                "category",
                "summary",
                "content",
                "image_path",
                "image_format",
                "image_size",
                "status",
            ]
            if not any(field in data for field in editable_fields):
                raise ValueError("missing update fields")
        else:
            required_fields = ["creator_user_id", "name", "category", "content"]
            missing_fields = [field for field in required_fields if data.get(field) in (None, "")]
            if missing_fields:
                raise ValueError(f"missing required fields: {', '.join(missing_fields)}")

        too_long_fields = []
        for field, max_length in cls._TEXT_LIMITS.items():
            value = data.get(field)
            if value is not None and len(str(value)) > max_length:
                too_long_fields.append(field)

        if too_long_fields:
            raise ValueError(f"fields exceed maximum length: {', '.join(too_long_fields)}")

        status = data.get("status")
        if status is not None and status not in {
            Community.STATUS_PUBLIC,
            Community.STATUS_PRIVATE,
            Community.STATUS_DELETED,
        }:
            raise ValueError("invalid status")

    @staticmethod
    def _community_to_dict(community: Community, actor: User | None = None) -> dict:
        payload = community.to_dict()
        can_edit = False
        if actor is not None:
            can_edit = actor.role == "admin" or community.creator_user_id == actor.id
        payload["can_edit"] = can_edit
        payload["can_delete"] = can_edit
        return payload

    @classmethod
    def check_community_permission(cls, community: Community, actor: User | None) -> bool:
        if actor is None:
            return False
        return actor.role == "admin" or community.creator_user_id == actor.id

    @classmethod
    def get_community_list(
        cls,
        *,
        search_keyword: str | None = None,
        category: str | None = None,
        auth_token: str | None = None,
    ) -> list[dict]:
        query = Community.query.filter(Community.status != Community.STATUS_DELETED)
        if search_keyword:
            like_pattern = f"%{search_keyword}%"
            query = query.filter(
                or_(
                    Community.name.ilike(like_pattern),
                    Community.summary.ilike(like_pattern),
                    Community.content.ilike(like_pattern),
                )
            )
        if category:
            query = query.filter(Community.category == category)

        actor = cls._get_user_by_auth_token(auth_token)
        communities = query.order_by(Community.updated_at.desc()).limit(cls.MAX_RESULTS).all()
        return [cls._community_to_dict(community, actor) for community in communities]

    @classmethod
    def get_community_detail(cls, community_id: int, auth_token: str | None = None) -> dict:
        community = db.session.get(Community, community_id)
        if community is None or community.status == Community.STATUS_DELETED:
            raise LookupError("community not found")
        actor = cls._get_user_by_auth_token(auth_token)
        return cls._community_to_dict(community, actor)

    @classmethod
    def save_community(cls, data: dict, community_id: int | None = None) -> dict:
        is_update = community_id is not None or data.get("community_id") is not None
        cls._validate_payload(data, is_update=is_update)

        actor = cls._resolve_actor(data)
        if actor is None:
            raise PermissionError("auth_token or creator_user_id is required")

        target_community_id = community_id if community_id is not None else data.get("community_id")
        if target_community_id is None:
            community = Community(
                creator_user_id=actor.id if data.get("auth_token") else data["creator_user_id"],
                name=data["name"],
                category=data["category"],
                summary=data.get("summary"),
                content=data["content"],
                image_path=data.get("image_path"),
                image_format=data.get("image_format"),
                image_size=data.get("image_size"),
                status=data.get("status", Community.STATUS_PUBLIC),
            )
            db.session.add(community)
            db.session.commit()
            return cls._community_to_dict(community, actor)

        community = db.session.get(Community, target_community_id)
        if community is None or community.status == Community.STATUS_DELETED:
            raise LookupError("community not found")
        if not cls.check_community_permission(community, actor):
            raise PermissionError("permission denied")

        editable_fields = [
            "name",
            "category",
            "summary",
            "content",
            "image_path",
            "image_format",
            "image_size",
            "status",
        ]
        for field in editable_fields:
            if field in data:
                setattr(community, field, data[field])

        db.session.commit()
        return cls._community_to_dict(community, actor)

    @classmethod
    def delete_community(cls, community_id: int, auth_token: str | None = None) -> dict:
        community = db.session.get(Community, community_id)
        if community is None or community.status == Community.STATUS_DELETED:
            raise LookupError("community not found")

        actor = cls._get_user_by_auth_token(auth_token)
        if not cls.check_community_permission(community, actor):
            raise PermissionError("permission denied")

        community.status = Community.STATUS_DELETED
        db.session.commit()
        return cls._community_to_dict(community, actor)


def list_communities() -> list[Community]:
    """後方互換のために残す。"""
    return Community.query.order_by(Community.updated_at.desc()).limit(CommunityService.MAX_RESULTS).all()


def create_community(data: dict) -> Community:
    """後方互換のために残す。"""
    payload = CommunityService.save_community(data)
    return db.session.get(Community, payload["id"])


def update_community(community: Community, data: dict) -> Community:
    """後方互換のために残す。"""
    updated = CommunityService.save_community({**data, "community_id": community.id})
    return db.session.get(Community, updated["id"])


def delete_community(community: Community) -> dict:
    """後方互換のために残す。"""
    return CommunityService.delete_community(community.id)
