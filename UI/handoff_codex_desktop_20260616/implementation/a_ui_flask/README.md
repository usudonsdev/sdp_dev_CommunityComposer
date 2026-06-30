# A担当: C1 UI処理部 Flask実装

このフォルダは、A担当範囲である **C1 UI処理部** だけをFlaskで実装する。

## 実装する範囲

- W1 ログイン画面
- W2 メイン画面
- W3 管理者用ログイン画面
- W4 コミュニティ作成・編集画面
- W5 コミュニティの詳細を表示する画面
- 画面側の最低限の入力チェック
- C2 認証処理部、C3 コミュニティ活動処理部へ処理を渡すための境界

## 実装しない範囲

- Google認証そのもの
- 管理者権限判定そのもの
- DB接続、DBテーブル定義
- F1ログイン情報、F2コミュニティ情報の永続化処理
- 参加申請、通知、勧誘、メンバー管理、検閲などの削除済み機能

## 起動

```powershell
cd implementation\a_ui_flask
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app wsgi run --debug
```

Google認証処理部が未接続の間に画面確認だけを行う場合は、次のURLで仮の `auth_token` をCookieに保存してから確認する。

```text
http://127.0.0.1:5000/auth/callback?auth_token=demo
```

その後、`http://127.0.0.1:5000/communities` を開く。

## C2/C3との接続

現段階では、C2/C3の仕様とDB仕様が未確定であるため、画面確認用の仮データを返す。

本接続時は以下の環境変数を設定する。

- `AUTH_GOOGLE_LOGIN_URL`
- `AUTH_ADMIN_GOOGLE_LOGIN_URL`
- `COMMUNITY_SERVICE_BASE_URL`

未設定の場合、一覧・詳細は仮データで表示し、保存・削除は「C3未接続」と表示する。
