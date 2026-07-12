# test_auth.py
from datetime import datetime
from datetime import timedelta
from unittest.mock import patch
from app.services.auth_service import AuthService
from run import app
from app.extensions import db
from app.models import User


def _verified_google_payload(*, email: str, hd: str = "shibaura-it.ac.jp") -> dict:
    return {
        "email": email,
        "email_verified": True,
        "hd": hd,
    }


def test_google_auth_flow():
    service = AuthService()

    with app.app_context():
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_google:
            mock_google.return_value = _verified_google_payload(
                email="test@shibaura-it.ac.jp"
            )

            auth_result = service.verify_google_account({"id_token": "dummy_valid_token"})
            assert auth_result["status"] == "OK"
            assert auth_result["email"] == "test@shibaura-it.ac.jp"

            user_id = auth_result["user_id"]
            admin_result = service.verify_admin_role(user_id=user_id)
            assert admin_result["status"] == "NG"

            current_time = datetime.now()
            token_result = service.issue_login_token(
                user_id=user_id,
                c_time=current_time,
            )
            assert token_result["status"] == "OK"

            updated_user = db.session.get(User, user_id)
            assert updated_user.auth_token

            verify_result = service.verify_login_token(
                auth_token=token_result["auth_token"],
                c_time=current_time,
            )
            assert verify_result["status"] == "OK"

            expired_result = service.verify_login_token(
                auth_token=token_result["auth_token"],
                c_time=current_time + timedelta(hours=25),
            )
            assert expired_result["status"] == "NG"

            mock_google.return_value = _verified_google_payload(
                email="stranger@other-univ.ac.jp",
                hd="other-univ.ac.jp",
            )

            other_auth_result = service.verify_google_account(
                {"id_token": "dummy_other_token"}
            )
            assert other_auth_result["status"] == "NG"
            assert "芝浦工業大学" in other_auth_result["reason"]


if __name__ == "__main__":
    test_google_auth_flow()
