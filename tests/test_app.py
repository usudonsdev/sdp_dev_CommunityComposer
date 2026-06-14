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
                "email": "student@shibaura-it.ac.jp",
                "auth_token": "token-1",
            },
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["user"]["email"] == "student@shibaura-it.ac.jp"
    assert body["user"]["role"] == "user"
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
            json={"summary": "Updated summary"},
        )
        delete_response = client.delete(f"/communities/{community['id']}")
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


def test_invalid_payload_returns_400():
    app = make_test_app()

    with app.test_client() as client:
        user_response = client.post("/users", json={})
        community_response = client.post("/communities", json={})

    assert user_response.status_code == 400
    assert community_response.status_code == 400


def test_admin_login_requires_secret():
    app = make_test_app()

    with app.test_client() as client:
        forbidden_response = client.post(
            "/admin/auth/login",
            json={"email": "admin@shibaura-it.ac.jp", "admin_secret": "wrong"},
        )
        ok_response = client.post(
            "/admin/auth/login",
            json={"email": "admin@shibaura-it.ac.jp", "admin_secret": "admin-secret"},
        )

    assert forbidden_response.status_code == 403
    assert ok_response.status_code == 200
    assert ok_response.get_json()["user"]["role"] == "admin"
<<<<<<< Updated upstream
=======


def test_user_login_creates_users_table_record():
    app = make_test_app()

    with app.test_client() as client:
        response = client.post(
            "/auth/login",
            json={
                "email": "student@shibaura-it.ac.jp",
                "auth_token": "token-1",
            },
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["user"]["email"] == "student@shibaura-it.ac.jp"
    assert body["user"]["role"] == "user"
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
                "auth_token": "token-2",
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


def test_community_list_supports_search_and_category_filter():
    app = make_test_app()

    with app.test_client() as client:
        creator_response = client.post(
            "/users",
            json={
                "email": "searcher@shibaura-it.ac.jp",
                "role": "user",
                "auth_token": "search-token",
            },
        )
        creator_id = creator_response.get_json()["user"]["id"]

        client.post(
            "/communities",
            json={
                "creator_user_id": creator_id,
                "auth_token": "search-token",
                "name": "Photography Club",
                "category": "Culture",
                "summary": "Photo walks and exhibitions",
                "content": "We study photography and share work.",
            },
        )
        client.post(
            "/communities",
            json={
                "creator_user_id": creator_id,
                "auth_token": "search-token",
                "name": "Robot Club",
                "category": "Engineering",
                "summary": "Robot project group",
                "content": "Members learn robot production and control.",
            },
        )

        search_response = client.get("/communities?q=Robot")
        filtered_response = client.get("/communities?category=Culture")

    assert search_response.status_code == 200
    assert [item["name"] for item in search_response.get_json()["communities"]] == [
        "Robot Club"
    ]
    assert [item["category"] for item in filtered_response.get_json()["communities"]] == [
        "Culture"
    ]


def test_community_update_requires_permission():
    app = make_test_app()

    with app.test_client() as client:
        creator_response = client.post(
            "/users",
            json={
                "email": "owner@shibaura-it.ac.jp",
                "role": "user",
                "auth_token": "owner-token",
            },
        )
        creator_id = creator_response.get_json()["user"]["id"]
        other_response = client.post(
            "/users",
            json={
                "email": "other@shibaura-it.ac.jp",
                "role": "user",
                "auth_token": "other-token",
            },
        )
        other_id = other_response.get_json()["user"]["id"]

        create_response = client.post(
            "/communities",
            json={
                "creator_user_id": creator_id,
                "auth_token": "owner-token",
                "name": "Board Game Club",
                "category": "Culture",
                "summary": "Play board games",
                "content": "We meet every week.",
            },
        )
        community_id = create_response.get_json()["community"]["id"]

        forbidden_update = client.put(
            f"/communities/{community_id}",
            json={"creator_user_id": other_id, "auth_token": "other-token", "summary": "hack"},
        )
        forbidden_delete = client.delete(
            f"/communities/{community_id}?auth_token=other-token"
        )

    assert forbidden_update.status_code == 403
    assert forbidden_delete.status_code == 403


def test_invalid_payload_returns_400():
    app = make_test_app()

    with app.test_client() as client:
        user_response = client.post("/users", json={})
        community_response = client.post("/communities", json={})

    assert user_response.status_code == 400
    assert community_response.status_code == 400


def test_admin_login_requires_secret():
    app = make_test_app()

    with app.test_client() as client:
        forbidden_response = client.post(
            "/admin/auth/login",
            json={"email": "admin@shibaura-it.ac.jp", "admin_secret": "wrong"},
        )
        ok_response = client.post(
            "/admin/auth/login",
            json={"email": "admin@shibaura-it.ac.jp", "admin_secret": "admin-secret"},
        )

    assert forbidden_response.status_code == 403
    assert ok_response.status_code == 200
    assert ok_response.get_json()["user"]["role"] == "admin"
>>>>>>> Stashed changes
