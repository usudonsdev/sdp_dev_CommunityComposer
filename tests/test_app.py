from app import create_app


def test_index_returns_application_name():
    app = create_app()

    with app.test_client() as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "CommunityComposer"
