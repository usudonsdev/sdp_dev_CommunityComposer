from flask import Blueprint, abort, jsonify, request

from app.extensions import db
from app.models.community import Community
from app.services.communities import (
    create_community,
    delete_community as delete_community_record,
    list_communities,
    update_community,
)


communities_bp = Blueprint("communities", __name__)


@communities_bp.get("/communities")
def get_communities():
    """コミュニティ一覧データを返す。"""
    communities = list_communities()
    return jsonify({"communities": [item.to_dict() for item in communities]}), 200


@communities_bp.post("/communities")
def post_community():
    """コミュニティデータを作成する。"""
    data = request.get_json(silent=True) or {}

    community = create_community(data)
    return jsonify({"community": community.to_dict()}), 201


@communities_bp.get("/communities/<int:community_id>")
def get_community(community_id: int):
    """コミュニティの詳細データを返す。"""
    community = db.session.get(Community, community_id)
    if community is None:
        abort(404)
    return jsonify({"community": community.to_dict()}), 200


@communities_bp.put("/communities/<int:community_id>")
def put_community(community_id: int):
    """コミュニティデータを更新する。"""
    community = db.session.get(Community, community_id)
    if community is None:
        abort(404)
    data = request.get_json(silent=True) or {}

    updated = update_community(community, data)
    return jsonify({"community": updated.to_dict()}), 200


@communities_bp.delete("/communities/<int:community_id>")
def delete_community(community_id: int):
    """コミュニティデータを削除する。"""
    community = db.session.get(Community, community_id)
    if community is None:
        abort(404)
    deleted = delete_community_record(community)
    return jsonify({"community": deleted}), 200
