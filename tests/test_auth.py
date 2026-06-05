# test_auth.py
from unittest.mock import patch
from app.services.auth_service import AuthService

def test_google_auth_flow():
    service = AuthService()

    # 1. Googleの検証関数（verify_oauth2_token）の動きを「偽装（patch）」する
    with patch('google.oauth2.id_token.verify_oauth2_token') as mock_google:
        
        # --- パターンA: 芝浦工大のアカウントで成功する場合のテスト ---
        # Googleが検証に成功し、この辞書データを返してきたと仮定します
        mock_google.return_value = {'email': 'taromaru@shibaura-it.ac.jp'}
        
        result = service.verify_google_account({'id_token': 'dummy_valid_token'})
        print("【テストA（正常系）の結果】:", result)
        # 期待値: statusがOKで、メールアドレスが返ってくること
        
        # --- パターンB: 他大学のアカウントでエラー（E2）になる場合のテスト ---
        mock_google.return_value = {'email': 'stranger@other-univ.ac.jp'}
        
        result = service.verify_google_account({'id_token': 'dummy_other_token'})
        print("【テストB（ドメインエラー）の結果】:", result)
        # 期待値: statusがNGで、「芝浦工業大学のアカウントではありません」となること

if __name__ == "__main__":
    test_google_auth_flow()