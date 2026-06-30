# tests/unittest_auth.py

import sys
import os
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch

# プロジェクトのルートディレクトリを検索パスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.auth_service import AuthService
from run import app
from app.extensions import db
from app.models import User

class TestAuthService(unittest.TestCase):

    def setUp(self):
        """ 各テストメソッドが実行される前の事前準備 """
        self.app_context = app.app_context()
        self.app_context.push()
        self.service = AuthService()
        
        # テスト用の固定データ
        self.email_student = "test-unit-student@shibaura-it.ac.jp"
        self.email_other = "attacker@gmail.com"
        
        # データベースをクリーンな状態にする（既存のテストデータを削除）
        self._clear_test_users()

    def tearDown(self):
        """ 各テストメソッドが終了した後の後片付け """
        self._clear_test_users()
        self.app_context.pop()

    def _clear_test_users(self):
        """ テスト用ユーザーをDBから削除するヘルパー関数 """
        for email in [self.email_student, self.email_other]:
            user = User.query.filter_by(email=email).first()
            if user:
                db.session.delete(user)
        db.session.commit()

    # =========================================================================
    # 1. verify_google_account 関数の単体テスト
    # =========================================================================

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_verify_google_account_success(self, mock_verify):
        """ [正常系] 正しいトークンかつ芝浦工大ドメインの場合、ユーザーが登録されOKになるか """
        mock_verify.return_value = {'email': self.email_student}
        
        result = self.service.verify_google_account({'id_token': 'valid_token'})
        
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["email"], self.email_student)
        self.assertIsNotNone(result["user_id"])

    def test_verify_google_account_no_token(self):
        """ [異常系] トークンが空の辞書で渡された場合、NG（トークンが存在しません）になるか """
        result = self.service.verify_google_account({})
        self.assertEqual(result["status"], "NG")
        self.assertIn("トークンが存在しません", result["reason"])

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_verify_google_account_invalid_domain(self, mock_verify):
        """ [異常系] 芝浦工大以外のドメインの場合、NG（ドメインエラー）として弾かれるか """
        mock_verify.return_value = {'email': self.email_other}
        
        result = self.service.verify_google_account({'id_token': 'external_token'})
        self.assertEqual(result["status"], "NG")
        self.assertIn("芝浦工業大学のGoogleアカウントではありません", result["reason"])

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_verify_google_account_value_error(self, mock_verify):
        """ [異常系] Google側の検証でエラー（ValueError）が起きた場合、NG（検証失敗）になるか """
        mock_verify.side_effect = ValueError("Invalid token structure")
        
        result = self.service.verify_google_account({'id_token': 'broken_token'})
        self.assertEqual(result["status"], "NG")
        self.assertIn("Google認証の検証に失敗しました", result["reason"])

    # =========================================================================
    # 2. verify_admin_role 関数の単体テスト
    # =========================================================================

    def test_verify_admin_role_user(self):
        """ [正常系] 一般ユーザー（role='user'）の場合、status='NG'（権限なし）で返るか """
        user = User(email=self.email_student, role="user")
        db.session.add(user)
        db.session.commit()

        # 引数を最新仕様（user_idのみ）に合わせて修正
        result = self.service.verify_admin_role(user.id)
        self.assertEqual(result["status"], "NG")
        self.assertEqual(result["role"], "user")
        self.assertIn("管理者権限がありません", result["reason"])

    def test_verify_admin_role_admin(self):
        """ [正常系] 管理者ユーザー（role='admin'）の場合、status='OK' で返るか """
        user = User(email=self.email_student, role="admin")
        db.session.add(user)
        db.session.commit()

        # 引数を最新仕様（user_idのみ）に合わせて修正
        result = self.service.verify_admin_role(user.id)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["role"], "admin")

    def test_verify_admin_role_not_found(self):
        """ [異常系] DBに存在しない偽のuser_idを指定した場合、NG（ユーザが見つかりません）になるか """
        result = self.service.verify_admin_role(99999)
        self.assertEqual(result["status"], "NG")
        self.assertIn("ユーザが見つかりません", result["reason"])

    # =========================================================================
    # 3. issue_login_token 関数の単体テスト
    # =========================================================================

    def test_issue_login_token_success(self):
        """ [正常系] トークンが正しく発行され、24時間後の有効期限がDBに保存されるか """
        user = User(email=self.email_student, role="user")
        db.session.add(user)
        db.session.commit()

        c_time = datetime(2026, 6, 16, 12, 0, 0)
        # 引数から余分な user.role を削除
        result = self.service.issue_login_token(user.id, c_time)

        self.assertEqual(result["status"], "OK")
        self.assertIsNotNone(result["auth_token"])
        self.assertEqual(result["expires_at"], "2026-06-17 12:00:00")

        # DBに保存された値も検証
        db_user = db.session.get(User, user.id)
        self.assertEqual(db_user.auth_token, result["auth_token"])
        self.assertEqual(db_user.token_expires_at, c_time + timedelta(hours=24))

    # =========================================================================
    # 4. verify_login_token 関数の単体テスト
    # =========================================================================

    def test_verify_login_token_within_expiry(self):
        """ [正常系・境界値] 期限内（発行から23時間59分後）のアクセスは正常に許可されるか """
        login_time = datetime(2026, 6, 16, 12, 0, 0)
        user = User(email=self.email_student, role="user", auth_token="token_xyz", token_expires_at=login_time + timedelta(hours=24))
        db.session.add(user)
        db.session.commit()

        access_time = login_time + timedelta(hours=23, minutes=59)
        result = self.service.verify_login_token("token_xyz", access_time)
        
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["user_id"], user.id)

    def test_verify_login_token_expired(self):
        """ [異常系・境界値] 期限切れ（発行から24時間1分後）のアクセスは拒否されるか """
        login_time = datetime(2026, 6, 16, 12, 0, 0)
        user = User(email=self.email_student, role="user", auth_token="token_xyz", token_expires_at=login_time + timedelta(hours=24))
        db.session.add(user)
        db.session.commit()

        access_time = login_time + timedelta(hours=24, minutes=1)
        result = self.service.verify_login_token("token_xyz", access_time)
        
        self.assertEqual(result["status"], "NG")
        self.assertIn("セッションの有効期限が切れています", result["reason"])
        self.assertIsNone(result["user_id"])  # assertNone を assertIsNone に修正


if __name__ == "__main__":
    unittest.main(verbosity=2)