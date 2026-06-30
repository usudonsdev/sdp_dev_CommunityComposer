from google.oauth2 import id_token
from google.auth.transport import requests
from app.extensions import db
from app.models import User
from datetime import timedelta
import secrets


# Google Cloud Consoleで取得した独自のクライアントIDが必要
GOOGLE_CLIENT_ID = "クライアントID.apps.googleusercontent.com"


class AuthService:
    """
    大学GoogleアカウントのGoogle認証情報を検証し、
    メールアドレスが@shibaura-it.ac.jpであることを確認する。
    認証後、管理者権限確認とログイントークン発行を行う。
    """

    def verify_google_account(self, google_auth: dict) -> dict:
        """
        Google認証情報を検証し、@shibaura-it.ac.jp であることを確認
        入力: google_auth (フロントから送信された {'id_token': 'xxxx'} などの辞書)
        出力: 認証結果（dict: OK/NG、ユーザID、メールアドレス）
        """
        # フロントエンドから送られてきたIDトークンを取り出す
        token = google_auth.get('id_token')
        if not token:
            return {"status": "NG", "reason": "トークンが存在しません"}
        
        try:
            # Googleの公式ライブラリを使ってトークンを検証・デコードする
            # これにより、有効期限のチェックやGoogleによるデジタル署名の検証が自動で行われる
            id_info = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
            
            # 検証に成功した場合、id_infoからユーザーのメールアドレス等の情報を取得
            email = id_info.get('email')
            
            # メールアドレスが芝浦工大のもの（@shibaura-it.ac.jp）かチェック（エラーE2のハンドリング）
            if not email or not email.endswith('@shibaura-it.ac.jp'):
                return {"status": "NG", "reason": "芝浦工業大学のGoogleアカウントではありません"}
            
            try:
                # DBからこのメールアドレスを持つユーザーを検索
                user = User.query.filter_by(email=email).first()
                
                # 初めてのログインなら新規登録
                if not user:
                    user = User(email=email, role="user") # roleはデフォルトで"user"
                    db.session.add(user)
                    db.session.commit()  # ここでSQLiteに保存され、自動で user.id が採番される
                
                # 確定した本物の id を取得
                user_id = user.id
                
            except Exception as e:
                # DB接続エラーやクエリエラーなどが発生した場合のハンドリング
                db.session.rollback()
                return {"status": "NG", "reason": f"データベースエラーが発生しました: {str(e)}"}
            
            return {
                "status": "OK",
                "user_id": user_id,
                "email": email
            }
            
        except ValueError:
            # トークンが無効、あるいは改ざんされていた場合
            return {"status": "NG", "reason": "Google認証の検証に失敗しました"}
    

    def verify_admin_role(self, user_id: int) -> dict:
        """
        ユーザが管理者権限を持つかを確認
        入力: ユーザID
        出力: 管理者認証結果OK/NG、権限種別
        """
        try:
            # DBからユーザIDに対応するユーザを取得
            user = User.query.get(user_id)

            # ユーザが見つからない場合
            if not user:
                return {
                    "status": "NG",
                    "reason": "ユーザが見つかりません",
                    "role": None
                }
            
            # ユーザが見つかった場合、roleを確認
            is_admin = (user.role == "admin")

            if is_admin:
                return {
                    "status": "OK",
                    "role": user.role
                }
            else:
                return {
                    "status": "NG",
                    "reason": "管理者権限がありません",
                    "role": user.role
                }
            
        except Exception as e:
            return {
                "status": "NG",
                "reason": f"エラーが発生しました: {str(e)}",
                "role": None
            }

    def issue_login_token(self, user_id: int, c_time) -> dict:
        """
        本システム内で利用するauth_tokenを発行
        入力: ユーザID、現在時刻
        出力: auth_token、有効期限、F1ログイン情報の更新結果
        """
        try:
            # 安全なランダムな文字列（トークン）を生成 (64文字)
            token = secrets.token_urlsafe(48)
            
            # DBから対象ユーザーを取得
            user = db.session.get(User, user_id)
            if not user:
                return {
                    "status": "NG",
                    "reason": "ユーザーが見つかりません。",
                    "auth_token": None
                }
            
            # トークンの有効期限を設定（発行から24時間後）
            expires_at = c_time + timedelta(hours=24)

            # ユーザーレコードの auth_token を更新
            user.auth_token = token
            user.token_expires_at = expires_at
            db.session.commit()
            
            return {
                "status": "OK",
                "auth_token": token,
                "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                "status": "NG",
                "reason": f"トークン発行中にデータベースエラーが発生しました: {str(e)}",
                "auth_token": None
            }

    def verify_login_token(self, auth_token: str, c_time) -> dict:
        """
        auth_tokenの有効性を検証
        入力: auth_token, 現在時刻
        出力: 認証結果OK/NG、ユーザID、権限種別
        """
        try:
            if not auth_token:
                return {"status": "NG", "reason": "トークンがありません。"}

            # DBからトークンに一致するユーザーを検索
            user = User.query.filter_by(auth_token=auth_token).first()

            if not user:
                return {"status": "NG", "reason": "無効なトークンです。"}

            # トークンの有効期限を確認
            if user.token_expires_at and c_time > user.token_expires_at:
                return {
                    "status": "NG",
                    "reason": "セッションの有効期限が切れています。",
                    "user_id": None, "role": None, "email": None
                }

            # 期限内ならOK
            return {
                "status": "OK",
                "user_id": user.id,
                "role": user.role,
                "email": user.email
            }
        except Exception as e:
            return {"status": "NG", "reason": str(e)}
