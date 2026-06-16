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

    try:
        community = create_community(data)
    except ValueError:
        return jsonify({"error": "invalid request payload"}), 400
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
from flask import Blueprint, jsonify, request

from app.services.communities import CommunityService


communities_bp = Blueprint("communities", __name__)


@communities_bp.get("/communities")
def get_communities():
    """コミュニティ一覧データを返す。"""
    communities = CommunityService.get_community_list(
        search_keyword=request.args.get("q"),
        category=request.args.get("category"),
        auth_token=request.args.get("auth_token"),
    )
    return jsonify({"communities": communities}), 200


@communities_bp.post("/communities")
def post_community():
    """コミュニティデータを作成する。"""
    data = request.get_json(silent=True) or {}

    try:
        community = CommunityService.save_community(data)
    except PermissionError:
        return jsonify({"error": "permission denied"}), 403
    except ValueError:
        return jsonify({"error": "invalid request payload"}), 400
    except LookupError:
        return jsonify({"error": "community not found"}), 404
    return jsonify({"community": community}), 201


@communities_bp.get("/communities/<int:community_id>")
def get_community(community_id: int):
    """コミュニティの詳細データを返す。"""
    try:
        community = CommunityService.get_community_detail(
            community_id,
            auth_token=request.args.get("auth_token"),
        )
    except LookupError:
        return jsonify({"error": "community not found"}), 404
    return jsonify({"community": community}), 200


@communities_bp.put("/communities/<int:community_id>")
def put_community(community_id: int):
    """コミュニティデータを更新する。"""
    data = request.get_json(silent=True) or {}
    data["community_id"] = community_id

    try:
        updated = CommunityService.save_community(data, community_id=community_id)
    except PermissionError:
        return jsonify({"error": "permission denied"}), 403
    except ValueError:
        return jsonify({"error": "invalid request payload"}), 400
    except LookupError:
        return jsonify({"error": "community not found"}), 404
    return jsonify({"community": updated}), 200


@communities_bp.delete("/communities/<int:community_id>")
def delete_community(community_id: int):
    """コミュニティデータを削除する。"""
    try:
        deleted = CommunityService.delete_community(
            community_id,
            auth_token=request.args.get("auth_token"),
        )
    except PermissionError:
        return jsonify({"error": "permission denied"}), 403
    except LookupError:
        return jsonify({"error": "community not found"}), 404
    return jsonify({"community": deleted}), 200
