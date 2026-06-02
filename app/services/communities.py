from app.extensions import db
from app.models.community import Community


def list_communities() -> list[Community]:
    """コミュニティ一覧を返す。"""
    return Community.query.order_by(Community.updated_at.desc()).limit(100).all()


def create_community(data: dict) -> Community:
    """コミュニティレコードを作成する。"""
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
