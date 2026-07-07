import os
import uuid
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename

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


@communities_bp.post("/communities/images")
def upload_image():
    """コミュニティ画像をアップロードする。"""
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename)
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".gif"]:
            return jsonify({"error": "Unsupported file extension"}), 400
        
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        upload_folder = os.path.join(current_app.root_path, "static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        image_size = os.path.getsize(file_path)
        image_format = ext.lstrip(".")
        image_path = f"/static/uploads/{unique_filename}"
        
        return jsonify({
            "image_path": image_path,
            "image_format": image_format,
            "image_size": image_size
        }), 201


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
