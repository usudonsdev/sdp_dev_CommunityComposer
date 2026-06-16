# test_auth.py
from datetime import datetime
from datetime import timedelta
from unittest.mock import patch
from app.services.auth_service import AuthService
from run import app
from app.extensions import db
from app.models import User


def test_google_auth_flow():
    service = AuthService()

    with app.app_context():

        # Googleの検証関数（verify_oauth2_token）の動きを「偽装（patch）」する
        with patch('google.oauth2.id_token.verify_oauth2_token') as mock_google:
            
            # --- パターンA: 芝浦工大のアカウントで成功する場合のテスト ---
            # Googleが検証に成功し、この辞書データを返してきたと仮定
            mock_google.return_value = {'email': 'test@shibaura-it.ac.jp'}
            
            auth_result = service.verify_google_account({'id_token': 'dummy_valid_token'})
            print("【テストA（正常系）の結果】:", auth_result)
            # 期待値: statusがOKで、メールアドレスが返ってくること

            #Google認証が成功した後、管理者権限の確認も行う
            if auth_result["status"] == "OK":
                user_id = auth_result["user_id"]
                admin_result = service.verify_admin_role(
                    user_id=user_id
                )
                print("\n【管理者権限確認結果】:", admin_result)

                # ログイントークンを発行する
                current_time = datetime.now()
                token_result = service.issue_login_token(
                    user_id=user_id,
                    c_time=current_time
                )
                print("\nログイントークン発行結果:", token_result)

                # 本当にDBにトークンが保存されたかダブルチェック
                updated_user = db.session.get(User, user_id)
                print(f"\n[DB確認] 保存されたトークン: {updated_user.auth_token[:10]}...")

            verify_result = service.verify_login_token(auth_token=token_result["auth_token"], c_time=current_time)
            print("\n【トークン検証結果(有効期限内)】:", verify_result)
            verify_result = service.verify_login_token(auth_token=token_result["auth_token"], c_time=(current_time + timedelta(hours=25)))
            print("\n【トークン検証結果(有効期限切れ)】:", verify_result)
            

            # --- パターンB: 他大学のアカウントでエラー（E2）になる場合のテスト ---
            mock_google.return_value = {'email': 'stranger@other-univ.ac.jp'}
            
            auth_result = service.verify_google_account({'id_token': 'dummy_other_token'})
            print("\n【テストB（ドメインエラー）の結果】:", auth_result)
            # 期待値: statusがNGで、「芝浦工業大学のアカウントではありません」となること

if __name__ == "__main__":
    test_google_auth_flow()