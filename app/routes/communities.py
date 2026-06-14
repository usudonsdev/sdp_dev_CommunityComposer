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
