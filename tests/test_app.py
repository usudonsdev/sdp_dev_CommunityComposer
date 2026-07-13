import os

from app import create_app


def make_test_app():
    """Build a fresh in-memory app for each test."""
    return create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "ADMIN_LOGIN_SECRET": "admin-secret",
        }
    )


def test_index_returns_application_name():
    app = make_test_app()

    with app.test_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "CommunityComposer"


def test_user_login_creates_users_table_record():
    app = make_test_app()

    with app.test_client() as client:
        response = client.post(
            "/auth/login",
            json={
                "mock_email_auth": "1",
                "email": "student@shibaura-it.ac.jp",
            },
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["user"]["email"] == "student@shibaura-it.ac.jp"
    assert body["user"]["role"] == "user"
    assert body["auth_token"]
    assert "auth_token" not in body["user"]


def test_community_create_reference_update_and_delete():
    app = make_test_app()

    with app.test_client() as client:
        user_response = client.post(
            "/users",
            json={
                "email": "creator@shibaura-it.ac.jp",
                "role": "user",
                "auth_token": "token-2",
            },
        )
        user_id = user_response.get_json()["user"]["id"]

        create_response = client.post(
            "/communities",
            json={
                "creator_user_id": user_id,
                "name": "Robot Club",
                "category": "Engineering",
                "summary": "Robot project group",
                "content": "Members learn robot production and control.",
                "image_path": "/uploads/robot.png",
                "image_format": "png",
                "image_size": 1024,
            },
        )
        community = create_response.get_json()["community"]

        list_response = client.get("/communities")
        detail_response = client.get(f"/communities/{community['id']}")
        update_response = client.put(
            f"/communities/{community['id']}",
            json={"summary": "Updated summary", "auth_token": "token-2"},
        )
        delete_response = client.delete(
            f"/communities/{community['id']}?auth_token=token-2"
        )
        deleted_detail_response = client.get(f"/communities/{community['id']}")
        after_delete_list_response = client.get("/communities")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert len(list_response.get_json()["communities"]) == 1
    assert detail_response.get_json()["community"]["name"] == "Robot Club"
    assert update_response.get_json()["community"]["summary"] == "Updated summary"
    assert delete_response.get_json()["community"]["name"] == "Robot Club"
    assert deleted_detail_response.status_code == 404
    assert after_delete_list_response.get_json()["communities"] == []


def test_community_update_and_delete_remove_old_image_files(monkeypatch):
    app = make_test_app()
    removed_paths = []

    def fake_remove(path):
        removed_paths.append(path)

    monkeypatch.setattr("app.services.communities.os.remove", fake_remove)

    with app.test_client() as client:
        user_response = client.post(
            "/users",
            json={
                "email": "creator2@shibaura-it.ac.jp",
                "role": "user",
                "auth_token": "token-3",
            },
        )
        user_id = user_response.get_json()["user"]["id"]

        create_response = client.post(
            "/communities",
            json={
                "creator_user_id": user_id,
                "name": "Photo Club",
                "category": "Arts",
                "summary": "Photo group",
                "content": "Members share photos.",
                "image_path": "/static/uploads/old.png",
                "image_format": "png",
                "image_size": 1024,
                "auth_token": "token-3",
            },
        )
        community = create_response.get_json()["community"]

        update_response = client.put(
            f"/communities/{community['id']}",
            json={
                "image_path": "/static/uploads/new.png",
                "image_format": "png",
                "image_size": 2048,
                "auth_token": "token-3",
            },
        )
        delete_response = client.delete(
            f"/communities/{community['id']}?auth_token=token-3"
        )

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert delete_response.status_code == 200
    assert removed_paths == [
        os.path.join(app.root_path, "static", "uploads", "old.png"),
        os.path.join(app.root_path, "static", "uploads", "new.png"),
    ]


def test_invalid_payload_returns_400():
    app = make_test_app()

    with app.test_client() as client:
        user_response = client.post("/users", json={})
        community_response = client.post("/communities", json={})

    assert user_response.status_code == 400
    assert community_response.status_code == 400


def test_admin_password_login():
    app = make_test_app()

    with app.test_client() as client:
        register_response = client.post(
            "/admin/auth/register",
            json={
                "email": "admin@shibaura-it.ac.jp",
                "password": "admin-secret",
            },
        )
        forbidden_response = client.post(
            "/admin/auth/login",
            json={
                "email": "admin@shibaura-it.ac.jp",
                "password": "wrong-secret",
            },
        )
        ok_response = client.post(
            "/admin/auth/login",
            json={
                "email": "admin@shibaura-it.ac.jp",
                "password": "admin-secret",
            },
        )

    assert register_response.status_code == 200
    assert register_response.get_json()["user"]["role"] == "admin"
    assert forbidden_response.status_code == 401
    assert ok_response.status_code == 200
    assert ok_response.get_json()["user"]["role"] == "admin"
    assert ok_response.get_json()["auth_token"]


def test_user_login_and_community_permission_flow():
    app = make_test_app()

    with app.test_client() as client:
        creator_login = client.post(
            "/auth/login",
            json={
                "mock_email_auth": "1",
                "email": "integration-creator@shibaura-it.ac.jp",
            },
        )
        other_login = client.post(
            "/auth/login",
            json={
                "mock_email_auth": "1",
                "email": "integration-other@shibaura-it.ac.jp",
            },
        )

        creator = creator_login.get_json()["user"]
        other = other_login.get_json()["user"]
        creator_token = creator_login.get_json()["auth_token"]
        other_token = other_login.get_json()["auth_token"]

        creator_detail = client.get(f"/users/{creator['id']}")
        assert creator_detail.status_code == 200
        assert creator_detail.get_json()["user"]["email"] == "integration-creator@shibaura-it.ac.jp"

        create_response = client.post(
            "/communities",
            json={
                "creator_user_id": creator["id"],
                "name": "Integration Club",
                "category": "Testing",
                "summary": "Integration test club",
                "content": "This flow checks cooperation between users and communities.",
                "auth_token": creator_token,
            },
        )
        community = create_response.get_json()["community"]

        list_response = client.get(f"/communities?auth_token={creator_token}")
        detail_response = client.get(
            f"/communities/{community['id']}?auth_token={creator_token}"
        )
        other_update_response = client.put(
            f"/communities/{community['id']}",
            json={
                "summary": "Should be forbidden",
                "auth_token": other_token,
            },
        )
        update_response = client.put(
            f"/communities/{community['id']}",
            json={
                "summary": "Integration summary updated",
                "auth_token": creator_token,
            },
        )
        delete_response = client.delete(
            f"/communities/{community['id']}?auth_token={creator_token}"
        )
        deleted_detail_response = client.get(f"/communities/{community['id']}")

    assert creator["email"] == "integration-creator@shibaura-it.ac.jp"
    assert other["email"] == "integration-other@shibaura-it.ac.jp"
    assert list_response.status_code == 200
    assert list_response.get_json()["communities"][0]["can_edit"] is True
    assert detail_response.get_json()["community"]["can_delete"] is True
    assert other_update_response.status_code == 403
    assert update_response.status_code == 200
    assert update_response.get_json()["community"]["summary"] == "Integration summary updated"
    assert delete_response.status_code == 200
    assert deleted_detail_response.status_code == 404


def test_user_routes_and_services_uncovered_paths():
    app = make_test_app()

    with app.test_client() as client:
        # login_user: missing email
        login_user_error = client.post("/auth/login", json={})
        assert login_user_error.status_code == 400

        # login_admin: missing password
        login_admin_error = client.post(
            "/admin/auth/login",
            json={"email": "admin@shibaura-it.ac.jp"},
        )
        assert login_admin_error.status_code == 400

        # get_user: not found
        get_user_error = client.get("/users/9999")
        assert get_user_error.status_code == 404

        # put_user: not found
        put_user_error = client.put("/users/9999", json={"email": "new@example.com"})
        assert put_user_error.status_code == 404

        # Create user
        user_response = client.post(
            "/users",
            json={
                "email": "test-user@shibaura-it.ac.jp",
                "role": "user",
                "auth_token": "token-user-1",
            },
        )
        user_id = user_response.get_json()["user"]["id"]

        # get_user: success (covers routes/users.py line 67)
        get_user_success = client.get(f"/users/{user_id}")
        assert get_user_success.status_code == 200
        assert get_user_success.get_json()["user"]["email"] == "test-user@shibaura-it.ac.jp"

        # update_user: test updates of email, role, and auth_token
        update_response = client.put(
            f"/users/{user_id}",
            json={
                "email": "updated-user@shibaura-it.ac.jp",
                "role": "admin",
                "auth_token": "token-user-2",
            },
        )
        assert update_response.status_code == 200
        updated_user = update_response.get_json()["user"]
        assert updated_user["email"] == "updated-user@shibaura-it.ac.jp"
        assert updated_user["role"] == "admin"


def test_community_routes_and_services_uncovered_paths():
    app = make_test_app()

    with app.test_client() as client:
        # Create creator user
        creator_resp = client.post(
            "/users",
            json={"email": "creator@shibaura-it.ac.jp", "auth_token": "token-creator"}
        )
        creator_id = creator_resp.get_json()["user"]["id"]

        # Create non-creator user
        other_resp = client.post(
            "/users",
            json={"email": "other@shibaura-it.ac.jp", "auth_token": "token-other"}
        )

        # 1. Validation error on creation (name too long)
        creation_long_name = client.post(
            "/communities",
            json={
                "creator_user_id": creator_id,
                "name": "a" * 100,
                "category": "Tech",
                "content": "Desc",
                "auth_token": "token-creator",
            }
        )
        assert creation_long_name.status_code == 400

        # 2. Validation error on creation (invalid status)
        creation_invalid_status = client.post(
            "/communities",
            json={
                "creator_user_id": creator_id,
                "name": "Test Comm",
                "category": "Tech",
                "content": "Desc",
                "status": "invalid_status",
                "auth_token": "token-creator",
            }
        )
        assert creation_invalid_status.status_code == 400

        # 3. Authorization error on creation (no creator_user_id and no auth_token)
        creation_no_actor = client.post(
            "/communities",
            json={"name": "Test Comm", "category": "Tech", "content": "Desc"}
        )
        assert creation_no_actor.status_code == 400

        # 3b. Authorization error on creation (invalid creator_user_id, no auth_token -> actor is None)
        creation_invalid_creator = client.post(
            "/communities",
            json={
                "creator_user_id": 9999,
                "name": "Test Comm",
                "category": "Tech",
                "content": "Desc",
            }
        )
        assert creation_invalid_creator.status_code == 403

        # Create valid community
        comm_resp = client.post(
            "/communities",
            json={
                "creator_user_id": creator_id,
                "name": "Tech Club",
                "category": "Technology",
                "summary": "Tech group",
                "content": "Learn coding",
                "auth_token": "token-creator",
            }
        )
        assert comm_resp.status_code == 201
        comm_id = comm_resp.get_json()["community"]["id"]

        # 4. Search filter by keyword
        search_keyword_resp = client.get("/communities?q=coding&auth_token=token-creator")
        assert search_keyword_resp.status_code == 200
        assert len(search_keyword_resp.get_json()["communities"]) > 0

        # 5. Search filter by category
        search_category_resp = client.get("/communities?category=Technology&auth_token=token-creator")
        assert search_category_resp.status_code == 200
        assert len(search_category_resp.get_json()["communities"]) > 0

        # 6. Detail error (non-existent ID)
        detail_error = client.get("/communities/9999")
        assert detail_error.status_code == 404

        # 7. Update error (non-existent ID)
        update_not_found = client.put(
            "/communities/9999",
            json={"name": "New Name", "auth_token": "token-creator"}
        )
        assert update_not_found.status_code == 404

        # 8. Update error (no permission using token-other)
        update_no_permission = client.put(
            f"/communities/{comm_id}",
            json={"name": "New Name", "auth_token": "token-other"}
        )
        assert update_no_permission.status_code == 403

        # 9. Update error (missing update fields)
        update_missing_fields = client.put(
            f"/communities/{comm_id}",
            json={"auth_token": "token-creator"}
        )
        assert update_missing_fields.status_code == 400

        # 9b. Update error (no auth_token and no creator_user_id, but has update field)
        update_no_actor = client.put(
            f"/communities/{comm_id}",
            json={"name": "New Name"}
        )
        assert update_no_actor.status_code == 403

        # 10. Update community via POST (using community_id parameter on non-existent community)
        post_update_not_found = client.post(
            "/communities",
            json={"community_id": 9999, "name": "New Name", "auth_token": "token-creator"}
        )
        assert post_update_not_found.status_code == 404

        # 11. Delete error (non-existent ID)
        delete_not_found = client.delete("/communities/9999?auth_token=token-creator")
        assert delete_not_found.status_code == 404

        # 12. Delete error (no permission)
        delete_no_permission = client.delete(f"/communities/{comm_id}?auth_token=token-other")
        assert delete_no_permission.status_code == 403

        # 13. Delete successfully
        delete_success = client.delete(f"/communities/{comm_id}?auth_token=token-creator")
        assert delete_success.status_code == 200

        # 14. Detail error (already deleted community)
        detail_deleted = client.get(f"/communities/{comm_id}")
        assert detail_deleted.status_code == 404

    # 15. check_community_permission with None actor (direct service call)
    from app.services.communities import CommunityService
    assert CommunityService.check_community_permission(None, None) is False


def test_legacy_backward_compatibility_functions():
    app = make_test_app()
    with app.app_context():
        # Create user
        from app.services.users import create_or_update_user
        user = create_or_update_user({"email": "legacy-creator@shibaura-it.ac.jp"})

        from app.services.communities import (
            create_community,
            list_communities,
            update_community,
            delete_community,
        )

        # create_community
        comm = create_community({
            "creator_user_id": user.id,
            "name": "Legacy Comm",
            "category": "Legacy",
            "content": "Legacy Desc"
        })
        assert comm is not None
        assert comm.name == "Legacy Comm"

        # list_communities
        lst = list_communities()
        assert len(lst) > 0

        # update_community (passing creator_user_id so it can resolve actor and allow permission)
        updated_comm = update_community(comm, {"name": "Updated Legacy Comm", "creator_user_id": user.id})
        assert updated_comm.name == "Updated Legacy Comm"

        # delete_community: raises PermissionError because it doesn't accept or pass auth_token/actor
        import pytest
        with pytest.raises(PermissionError):
            delete_community(comm)


def test_image_upload_routes():
    app = make_test_app()
    with app.test_client() as client:
        # 1. Uploading without file field
        no_file_resp = client.post("/communities/images")
        assert no_file_resp.status_code == 400
        
        # 2. Uploading empty filename
        import io
        empty_filename_resp = client.post(
            "/communities/images",
            data={"image": (io.BytesIO(b""), "")},
            content_type="multipart/form-data"
        )
        assert empty_filename_resp.status_code == 400
        
        # 3. Uploading unsupported extension
        invalid_ext_resp = client.post(
            "/communities/images",
            data={"image": (io.BytesIO(b"fake data"), "test.txt")},
            content_type="multipart/form-data"
        )
        assert invalid_ext_resp.status_code == 400
        
        # 4. Uploading valid image (using Japanese filename to test the secure_filename fix)
        valid_resp = client.post(
            "/communities/images",
            data={"image": (io.BytesIO(b"fake image data"), "画像.png")},
            content_type="multipart/form-data"
        )
        assert valid_resp.status_code == 201
        json_data = valid_resp.get_json()
        assert json_data["image_format"] == "png"
        assert json_data["image_size"] > 0
        assert json_data["image_path"].startswith("/static/uploads/")
