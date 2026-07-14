from app import create_app


def make_test_app():
    app = create_app({"TESTING": True, "ADMIN_LOGIN_SECRET": "admin-secret"})
    return app


def test_register_and_login_with_password():
    app = make_test_app()

    with app.test_client() as client:
        register_response = client.post(
            "/auth/register",
            json={
                "email": "student@shibaura-it.ac.jp",
                "password": "secret123",
            },
        )
        login_response = client.post(
            "/auth/login",
            json={
                "email": "student@shibaura-it.ac.jp",
                "password": "secret123",
            },
        )
        wrong_password_response = client.post(
            "/auth/login",
            json={
                "email": "student@shibaura-it.ac.jp",
                "password": "wrong-pass",
            },
        )

    assert register_response.status_code == 200
    assert register_response.get_json()["auth_token"]
    assert register_response.get_json()["message"] == "登録が完了しました。"

    assert login_response.status_code == 200
    assert login_response.get_json()["auth_token"]
    assert login_response.get_json()["user"]["email"] == "student@shibaura-it.ac.jp"

    assert wrong_password_response.status_code == 401


def test_register_rejects_short_password():
    app = make_test_app()

    with app.test_client() as client:
        response = client.post(
            "/auth/register",
            json={
                "email": "short@shibaura-it.ac.jp",
                "password": "abc",
            },
        )

    assert response.status_code == 400
    assert "8文字" in response.get_json()["error"]


def test_register_rejects_duplicate_email():
    app = make_test_app()

    with app.test_client() as client:
        first = client.post(
            "/auth/register",
            json={
                "email": "dup@shibaura-it.ac.jp",
                "password": "secret123",
            },
        )
        second = client.post(
            "/auth/register",
            json={
                "email": "dup@shibaura-it.ac.jp",
                "password": "other1234",
            },
        )

    assert first.status_code == 200
    assert second.status_code == 409


def test_admin_register_and_login_with_password():
    app = make_test_app()

    with app.test_client() as client:
        register_response = client.post(
            "/admin/auth/register",
            json={
                "email": "adminAL24000@shibaura-it.ac.jp",
                "password": "adminpass1",
            },
        )
        login_response = client.post(
            "/admin/auth/login",
            json={
                "email": "adminAL24000@shibaura-it.ac.jp",
                "password": "adminpass1",
            },
        )

    assert register_response.status_code == 200
    assert register_response.get_json()["user"]["role"] == "admin"
    assert login_response.status_code == 200
    assert login_response.get_json()["user"]["role"] == "admin"


def test_login_requires_password_when_not_using_mock():
    app = make_test_app()

    with app.test_client() as client:
        response = client.post(
            "/auth/login",
            json={"email": "missing@shibaura-it.ac.jp"},
        )

    assert response.status_code == 400
    assert "パスワード" in response.get_json()["error"]
