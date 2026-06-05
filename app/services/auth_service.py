from google.oauth2 import id_token
from google.auth.transport import requests

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
            # 1. Googleの公式ライブラリを使ってトークンを検証・デコードする
            # これにより、有効期限のチェックやGoogleによるデジタル署名の検証が自動で行われる
            id_info = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
            
            # 2. 検証に成功した場合、id_infoからユーザーのメールアドレス等の情報を取得
            email = id_info.get('email')
            
            # 3. メールアドレスが芝浦工大のもの（@shibaura-it.ac.jp）かチェック（エラーE2のハンドリング）
            if not email or not email.endswith('@shibaura-it.ac.jp'):
                return {"status": "NG", "reason": "芝浦工業大学のGoogleアカウントではありません"}
            
            # 4. DB（F1 ログイン情報）を参照し、該当するuser_idを取得する処理（無ければ新規登録）
            # ここでは例として仮の値を設定します
            user_id = 123  
            
            return {
                "status": "OK",
                "user_id": user_id,
                "email": email
            }
            
        except ValueError:
            # トークンが無効、あるいは改ざんされていた場合
            return {"status": "NG", "reason": "Google認証の検証に失敗しました"}
    

    def verify_admin_role(self, user_id: int, email: str) -> dict:
        """
        ユーザが管理者権限を持つかを確認
        入力: ユーザID、メールアドレス、F1ログイン情報
        出力: 管理者認証結果OK/NG、権限種別
        """
        

    def issue_login_token(self, user_id: int, role: str, c_time) -> dict:
        """
        本システム内で利用するauth_tokenを発行
        入力: ユーザID、権限種別、現在時刻
        出力: auth_token、有効期限、F1ログイン情報の更新結果
        """


    def verify_login_token(self, auth_token: str) -> dict:
        """
        auth_tokenの有効性を検証
        入力: auth_token
        出力: 認証結果OK/NG、ユーザID、権限種別
        """
